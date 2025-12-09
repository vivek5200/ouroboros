"""
Phase 4: Diffusion Configuration
==================================

Configuration for discrete diffusion models used in code generation.
"""

import os
from enum import Enum
from typing import Optional
from dataclasses import dataclass


class DiffusionBackbone(Enum):
    """Available backbone models for diffusion."""
    QWEN25_CODER_15B = "qwen2.5-coder-1.5b"  # Lightweight, fast
    QWEN25_CODER_7B = "qwen2.5-coder-7b"      # Balanced
    QWEN25_CODER_14B = "qwen2.5-coder-14b"    # High quality
    MOCK = "mock"  # For testing


class NoiseSchedule(Enum):
    """Noise schedules for diffusion process."""
    LINEAR = "linear"
    COSINE = "cosine"
    SQRT = "sqrt"


@dataclass
class DiffusionConfig:
    """Configuration for diffusion-based code generation."""
    
    # Model configuration
    backbone: DiffusionBackbone = DiffusionBackbone.QWEN25_CODER_15B
    device: str = "cuda"  # "cuda", "cpu", "mps"
    dtype: str = "float16"  # "float16", "float32", "bfloat16"
    
    # Diffusion process parameters
    num_diffusion_steps: int = 1000  # Total timesteps
    num_sampling_steps: int = 50     # Steps during inference (< total)
    noise_schedule: NoiseSchedule = NoiseSchedule.COSINE
    beta_start: float = 0.0001
    beta_end: float = 0.02
    
    # Generation parameters
    cfg_guidance_scale: float = 7.5  # Classifier-free guidance strength
    temperature: float = 0.8
    top_p: float = 0.95
    top_k: int = 50
    
    # AST masking configuration
    mask_ratio: float = 0.3  # Fraction of code to mask
    preserve_syntax: bool = True
    
    # Performance
    batch_size: int = 1
    max_sequence_length: int = 2048
    
    # Checkpointing
    checkpoint_path: Optional[str] = None
    enable_gradient_checkpointing: bool = True
    
    # Validation
    validate_syntax: bool = True  # Use Tree-Sitter validation
    max_validation_attempts: int = 3
    
    @classmethod
    def from_env(cls) -> "DiffusionConfig":
        """Load configuration from environment variables."""
        return cls(
            backbone=DiffusionBackbone(os.getenv("DIFFUSION_BACKBONE", "qwen2.5-coder-1.5b")),
            device=os.getenv("DIFFUSION_DEVICE", "cuda"),
            dtype=os.getenv("DIFFUSION_DTYPE", "float16"),
            num_diffusion_steps=int(os.getenv("DIFFUSION_STEPS", "1000")),
            num_sampling_steps=int(os.getenv("SAMPLING_STEPS", "50")),
            cfg_guidance_scale=float(os.getenv("CFG_SCALE", "7.5")),
            temperature=float(os.getenv("TEMPERATURE", "0.8")),
        )
    
    def validate(self) -> None:
        """Validate configuration parameters."""
        assert 0 < self.mask_ratio <= 1.0, "mask_ratio must be in (0, 1]"
        assert self.num_sampling_steps <= self.num_diffusion_steps
        assert self.cfg_guidance_scale >= 1.0, "CFG scale should be >= 1.0"
        assert 0 < self.temperature <= 2.0
        assert 0 < self.top_p <= 1.0


# Default configurations for different use cases
FAST_CONFIG = DiffusionConfig(
    backbone=DiffusionBackbone.QWEN25_CODER_15B,
    num_sampling_steps=20,
    cfg_guidance_scale=5.0,
    temperature=0.7,
)

BALANCED_CONFIG = DiffusionConfig(
    backbone=DiffusionBackbone.QWEN25_CODER_7B,
    num_sampling_steps=50,
    cfg_guidance_scale=7.5,
    temperature=0.8,
)

QUALITY_CONFIG = DiffusionConfig(
    backbone=DiffusionBackbone.QWEN25_CODER_14B,
    num_sampling_steps=100,
    cfg_guidance_scale=10.0,
    temperature=0.6,
)

MOCK_CONFIG = DiffusionConfig(
    backbone=DiffusionBackbone.MOCK,
    num_sampling_steps=5,
    device="cpu",
)


def get_config(preset: str = "balanced") -> DiffusionConfig:
    """
    Get diffusion configuration by preset name.
    
    Args:
        preset: One of "fast", "balanced", "quality", "mock"
    
    Returns:
        DiffusionConfig instance
    """
    configs = {
        "fast": FAST_CONFIG,
        "balanced": BALANCED_CONFIG,
        "quality": QUALITY_CONFIG,
        "mock": MOCK_CONFIG,
    }
    
    if preset not in configs:
        raise ValueError(f"Unknown preset: {preset}. Choose from {list(configs.keys())}")
    
    return configs[preset]
