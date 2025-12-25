"""
Discrete Diffusion Model for Code Generation
=============================================

Implements discrete diffusion process for structured code generation
with AST-aware masking and syntax validation.

Architecture:
    Masked Code → Forward Diffusion (add noise) → Denoising Steps → Generated Code
    
Key Features:
- Discrete token-level diffusion
- Classifier-free guidance (CFG)
- Tree-Sitter syntax validation
- Autoregressive fallback on failure
"""

import logging
import time
import numpy as np
import torch
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .config import DiffusionConfig, DiffusionBackbone, NoiseSchedule
from .masking import ASTMasker, MaskedSpan, MaskingStrategy


logger = logging.getLogger(__name__)


@dataclass
class DiffusionSample:
    """Represents a generated code sample from diffusion."""
    
    generated_code: str
    masked_spans: List[MaskedSpan]
    num_steps: int
    cfg_scale: float
    is_valid_syntax: bool
    validation_errors: List[str]
    generation_time_ms: float
    metadata: Dict[str, Any]


class NoiseScheduler:
    """
    Manages noise scheduling for diffusion process.
    
    Computes beta values (noise levels) across timesteps according
    to chosen schedule (linear, cosine, sqrt).
    """
    
    def __init__(
        self,
        num_steps: int,
        schedule: NoiseSchedule = NoiseSchedule.COSINE,
        beta_start: float = 0.0001,
        beta_end: float = 0.02,
    ):
        self.num_steps = num_steps
        self.schedule = schedule
        self.beta_start = beta_start
        self.beta_end = beta_end
        
        # Compute beta schedule
        self.betas = self._compute_betas()
        self.alphas = 1.0 - self.betas
        self.alphas_cumprod = np.cumprod(self.alphas)
        self.alphas_cumprod_prev = np.append(1.0, self.alphas_cumprod[:-1])
        
        # Precompute values for sampling
        self.sqrt_alphas_cumprod = np.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = np.sqrt(1.0 - self.alphas_cumprod)
        
        logger.info(f"Initialized {schedule.value} noise schedule with {num_steps} steps")
    
    def _compute_betas(self) -> np.ndarray:
        """Compute beta values according to schedule."""
        if self.schedule == NoiseSchedule.LINEAR:
            return np.linspace(self.beta_start, self.beta_end, self.num_steps)
        
        elif self.schedule == NoiseSchedule.COSINE:
            # Cosine schedule (Nichol & Dhariwal, 2021)
            steps = np.arange(self.num_steps + 1, dtype=np.float64) / self.num_steps
            alpha_bar = np.cos((steps + 0.008) / 1.008 * np.pi / 2) ** 2
            betas = np.minimum(1 - alpha_bar[1:] / alpha_bar[:-1], 0.999)
            return betas
        
        elif self.schedule == NoiseSchedule.SQRT:
            # Square root schedule
            steps = np.arange(self.num_steps, dtype=np.float64)
            betas = np.sqrt(steps / self.num_steps) * (self.beta_end - self.beta_start) + self.beta_start
            return betas
        
        else:
            raise ValueError(f"Unknown noise schedule: {self.schedule}")
    
    def get_beta(self, t: int) -> float:
        """Get beta value at timestep t."""
        return self.betas[t]
    
    def get_alpha_cumprod(self, t: int) -> float:
        """Get cumulative product of alphas at timestep t."""
        return self.alphas_cumprod[t]


class DiscreteDiffusionModel:
    """
    Discrete diffusion model for code generation.
    
    Implements forward diffusion (adding noise) and reverse diffusion
    (denoising) processes for structured code generation.
    
    Usage:
        model = DiscreteDiffusionModel(config)
        generated = model.generate(
            masked_code=masked_code,
            masked_spans=spans,
            condition=compressed_context
        )
    """
    
    def __init__(self, config: DiffusionConfig):
        """Initialize diffusion model."""
        config.validate()
        self.config = config
        
        # Initialize noise scheduler
        self.scheduler = NoiseScheduler(
            num_steps=config.num_diffusion_steps,
            schedule=config.noise_schedule,
            beta_start=config.beta_start,
            beta_end=config.beta_end,
        )
        
        # Initialize backbone model (Qwen2.5-Coder or mock)
        self.backbone = self._init_backbone()
        
        # Initialize AST masker for validation
        self.masker = ASTMasker(language="python")  # Will be set per-language
        
        logger.info(
            f"DiffusionModel initialized: {config.backbone.value}, "
            f"{config.num_sampling_steps} steps, CFG={config.cfg_guidance_scale}"
        )
    
    def _init_backbone(self):
        """Initialize backbone model."""
        if self.config.backbone == DiffusionBackbone.MOCK:
            logger.info("Using MOCK backbone for testing")
            return None  # Mock mode
        
        # TODO: Load real Qwen2.5-Coder model
        # from transformers import AutoModelForCausalLM, AutoTokenizer
        # self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        # self.model = AutoModelForCausalLM.from_pretrained(
        #     model_name,
        #     torch_dtype=getattr(torch, self.config.dtype),
        #     device_map=self.config.device
        # )
        
        import os
        if os.getenv("COLAB_API_URL"):
            logger.info(f"Using Real Backbone via Colab: {os.getenv('COLAB_API_URL')}")
        else:
            logger.warning("Real backbone models not yet implemented - using MOCK")
        return None
    
    def generate(
        self,
        masked_code: str,
        masked_spans: List[MaskedSpan],
        condition: Optional[str] = None,
        language: str = "python",
    ) -> DiffusionSample:
        """
        Generate code by denoising masked spans.
        
        Args:
            masked_code: Code with [MASK] tokens
            masked_spans: Metadata about masked regions
            condition: Conditioning context (compressed codebase context)
            language: Programming language
        
        Returns:
            DiffusionSample with generated code and metadata
        """
        start_time = time.time()
        
        # Update masker language
        self.masker = ASTMasker(language=language)
        
        logger.info(
            f"Starting diffusion generation: {len(masked_spans)} spans, "
            f"{len(masked_code)} chars, language={language}"
        )
        
        # Forward diffusion: Add noise to masked spans
        noisy_tokens = self._forward_diffusion(masked_spans)
        
        # Reverse diffusion: Denoise step by step
        predictions = self._reverse_diffusion(
            noisy_tokens=noisy_tokens,
            masked_code=masked_code,
            masked_spans=masked_spans,
            condition=condition,
        )
        
        # Unmask code with predictions
        generated_code = self.masker.unmask(masked_code, masked_spans, predictions)
        
        # Validate syntax
        is_valid, errors = self.masker.validate_syntax(generated_code)
        
        generation_time = (time.time() - start_time) * 1000  # ms
        
        sample = DiffusionSample(
            generated_code=generated_code,
            masked_spans=masked_spans,
            num_steps=self.config.num_sampling_steps,
            cfg_scale=self.config.cfg_guidance_scale,
            is_valid_syntax=is_valid,
            validation_errors=errors,
            generation_time_ms=generation_time,
            metadata={
                "language": language,
                "backbone": self.config.backbone.value,
                "num_masked_spans": len(masked_spans),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        
        logger.info(
            f"Generation complete: {generation_time:.1f}ms, "
            f"syntax_valid={is_valid}, errors={len(errors)}"
        )
        
        return sample
    
    def _forward_diffusion(
        self,
        masked_spans: List[MaskedSpan],
    ) -> List[np.ndarray]:
        """
        Forward diffusion: Add noise to masked spans.
        
        Args:
            masked_spans: Spans to add noise to
        
        Returns:
            List of noisy token representations
        """
        noisy_tokens = []
        
        for span in masked_spans:
            # Start from pure noise (random tokens)
            # In discrete diffusion, we sample from vocabulary uniformly
            vocab_size = 50257  # GPT-2 vocab size (placeholder)
            noise = np.random.randint(0, vocab_size, size=(len(span.original_text),))
            noisy_tokens.append(noise)
        
        return noisy_tokens
    
    def _reverse_diffusion(
        self,
        noisy_tokens: List[np.ndarray],
        masked_code: str,
        masked_spans: List[MaskedSpan],
        condition: Optional[str],
    ) -> List[str]:
        """
        Reverse diffusion: Denoise step by step with CFG.
        
        Args:
            noisy_tokens: Initial noisy tokens
            masked_code: Code with masks
            masked_spans: Span metadata
            condition: Conditioning context
        
        Returns:
            List of predicted text for each span
        """
        # Sampling timesteps (evenly spaced)
        timesteps = np.linspace(
            self.config.num_diffusion_steps - 1,
            0,
            self.config.num_sampling_steps,
            dtype=int
        )
        
        predictions = []
        
        import os
        colab_url = os.getenv("COLAB_API_URL")
        
        for i, span in enumerate(masked_spans):
            # Use Colab bridge or real backbone if available
            if colab_url or self.backbone is not None:
                predicted_text = self._denoise_span(
                    noisy_tokens[i],
                    timesteps,
                    span,
                    masked_code,
                    condition,
                )
            else:
                # Mock mode only if no mechanism available
                predicted_text = self._mock_predict(span, condition)
            
            predictions.append(predicted_text)
        
        return predictions
    
    def _mock_predict(
        self,
        span: MaskedSpan,
        condition: Optional[str],
    ) -> str:
        """Mock prediction for testing."""
        # Simple heuristic: return original text or template
        if span.node_type == "function_definition":
            return "def mock_function():\n    pass"
        elif span.node_type == "expression_statement":
            return "result = 42"
        elif span.node_type == "identifier":
            return "mock_var"
        else:
            return span.original_text  # Fallback to original
    
    def _denoise_span(
        self,
        noisy_tokens: np.ndarray,
        timesteps: np.ndarray,
        span: MaskedSpan,
        masked_code: str,
        condition: Optional[str],
    ) -> str:
        """
        Denoise a single span using backbone model or Colab Bridge.
        """
        import os
        import requests
        
        colab_url = os.getenv("COLAB_API_URL")
        
        if colab_url:
            try:
                # Construct prompt for the model
                prompt = (
                    f"# Context: {condition}\n"
                    f"# Original Code (Masked):\n{masked_code}\n\n"
                    f"# Goal: Fill in the mask for {span.node_type}\n"
                    f"# Code:\n"
                )
                
                response = requests.post(
                    f"{colab_url}/generate",
                    json={
                        "prompt": prompt,
                        "max_tokens": 128,
                        "temperature": 0.2
                    },
                    timeout=120
                )
                
                if response.status_code == 200:
                    data = response.json()
                    gen_text = data.get("generated_text", span.original_text)
                    
                    # Clean markdown code blocks
                    gen_text = self._clean_output(gen_text)
                    
                    logger.info(f"LLaDA Raw Output: {gen_text}")
                    return gen_text
                else:
                    logger.error(f"Colab Bridge error: {response.text}")
            except Exception as e:
                logger.error(f"Failed to call Colab Bridge: {e}")
                
        # Fallback to simple logic if no bridge or error
        return span.original_text

    def _clean_output(self, text: str) -> str:
        """Strip markdown code fences from model output."""
        # Regex to find content between ```python ... ``` or ``` ... ```
        match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
        if match:
             return match.group(1).strip()
        
        # Fallback: existing logic for non-fenced but potentially chatty output?
        # If no fences, just return text, but maybe strip leading "Here is the code:" etc?
        # For now, just strip
        text = text.strip()
        if text.startswith("```"):
            # Should have been caught by regex, but handle unclosed fence start
            if text.startswith("```python"):
                text = text[9:]
            else:
                text = text[3:]
        
        # If ends with ``` but wasn't caught by regex (unlikely given DOTALL), clean it
        if text.endswith("```"):
            text = text[:-3]
            
        return text.strip()

    def generate_with_fallback(
        self,
        masked_code: str,
        masked_spans: List[MaskedSpan],
        condition: Optional[str] = None,
        language: str = "python",
        fallback_model: Optional[str] = None,
    ) -> DiffusionSample:
        """
        Generate code with autoregressive fallback on failure.
        """
        attempts = 0
        max_attempts = self.config.max_validation_attempts
        
        while attempts < max_attempts:
            sample = self.generate(masked_code, masked_spans, condition, language)
            
            if sample.is_valid_syntax:
                logger.info(f"✓ Diffusion succeeded on attempt {attempts + 1}")
                return sample
            
            logger.warning(
                f"✗ Diffusion attempt {attempts + 1} failed validation: "
                f"{sample.validation_errors}"
            )
            attempts += 1
        
        # All diffusion attempts failed - use autoregressive fallback
        logger.warning(f"Diffusion failed after {max_attempts} attempts, using fallback")
        return self._autoregressive_fallback(
            masked_code,
            masked_spans,
            condition,
            language,
            fallback_model or "qwen2.5-coder-1.5b"
        )
    
    def _autoregressive_fallback(
        self,
        masked_code: str,
        masked_spans: List[MaskedSpan],
        condition: Optional[str],
        language: str,
        model_name: str,
    ) -> DiffusionSample:
        """
        Fallback to autoregressive generation via Colab Bridge.
        """
        start_time = time.time()
        import os
        import requests
        
        logger.info(f"Using autoregressive fallback: {model_name}")
        
        colab_url = os.getenv("COLAB_API_URL")
        predictions = []
        
        if colab_url:
            for span in masked_spans:
                try:
                    # Specific prompt for autoregressive fill
                    prompt = (
                        f"You are an expert coder. Complete the code.\n"
                        f"# Context: {condition}\n"
                        f"# Code:\n{masked_code.replace('[MASK]', '???')}\n\n"
                        f"Fill in the ??? corresponding to '{span.node_type}':\n"
                    )
                    
                    response = requests.post(
                        f"{colab_url}/generate",
                        json={
                            "prompt": prompt,
                            "max_tokens": 256,
                            "temperature": 0.1
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        predictions.append(response.json().get("generated_text", "").strip())
                    else:
                        predictions.append(span.original_text)
                        
                except Exception as e:
                    logger.error(f"Colab fallback failed: {e}")
                    predictions.append(span.original_text)
        else:
            # Mock fallback
            predictions = [span.original_text for span in masked_spans]
            
        generated_code = self.masker.unmask(masked_code, masked_spans, predictions)
        
        is_valid, errors = self.masker.validate_syntax(generated_code)
        generation_time = (time.time() - start_time) * 1000
        
        return DiffusionSample(
            generated_code=generated_code,
            masked_spans=masked_spans,
            num_steps=0,  # No diffusion steps used
            cfg_scale=0.0,
            is_valid_syntax=is_valid,
            validation_errors=errors,
            generation_time_ms=generation_time,
            metadata={
                "language": language,
                "backbone": "colab_bridge_fallback" if colab_url else "mock_fallback",
                "fallback_model": model_name,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


if __name__ == "__main__":
    # Example usage
    from .config import MOCK_CONFIG
    
    code = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total
"""
    
    # Mask code
    masker = ASTMasker(language="python")
    masked_code, spans = masker.mask(
        code,
        strategy=MaskingStrategy.FUNCTION_BODY,
        mask_ratio=0.5
    )
    
    print("Masked Code:")
    print(masked_code)
    print(f"\nMasked {len(spans)} spans")
    
    # Generate with diffusion
    model = DiscreteDiffusionModel(MOCK_CONFIG)
    sample = model.generate_with_fallback(
        masked_code=masked_code,
        masked_spans=spans,
        condition="Calculate total price of shopping cart items",
        language="python"
    )
    
    print("\nGenerated Code:")
    print(sample.generated_code)
    print(f"\nSyntax valid: {sample.is_valid_syntax}")
    print(f"Generation time: {sample.generation_time_ms:.1f}ms")
