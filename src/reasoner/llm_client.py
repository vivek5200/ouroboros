"""
Abstract LLM client interface with provider implementations.

Implements the Strategy pattern for swapping LLM providers while maintaining
a consistent interface. Includes retry logic, rate limiting, and error handling.
"""

import time
import json
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .config import ReasonerConfig, LLMProvider, ModelConfig


logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    
    content: str
    model: str
    provider: LLMProvider
    
    # Token usage
    input_tokens: int
    output_tokens: int
    total_tokens: int
    
    # Metadata
    finish_reason: str
    latency_ms: float
    cost_usd: float
    
    # Raw response for debugging
    raw_response: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider.value,
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
                "total": self.total_tokens,
            },
            "finish_reason": self.finish_reason,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
        }


class LLMClient(ABC):
    """
    Abstract base class for LLM providers.
    
    All provider implementations must inherit from this class and implement
    the generate() method. This ensures consistent behavior across providers.
    """
    
    def __init__(self, config: ReasonerConfig):
        self.config = config
        self.model_config = config.model_config
        self._setup_client()
    
    @abstractmethod
    def _setup_client(self):
        """Initialize provider-specific client."""
        pass
    
    @abstractmethod
    def _generate_impl(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Provider-specific generation implementation."""
        pass
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response with retry logic and error handling.
        
        Args:
            system_prompt: System instructions for the LLM
            user_prompt: User query/task
            **kwargs: Additional provider-specific parameters
        
        Returns:
            LLMResponse with generated content and metadata
        
        Raises:
            LLMGenerationError: If all retry attempts fail
        """
        
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"LLM generation attempt {attempt + 1}/{self.config.max_retries}")
                
                start_time = time.time()
                response = self._generate_impl(system_prompt, user_prompt, **kwargs)
                latency_ms = (time.time() - start_time) * 1000
                
                response.latency_ms = latency_ms
                
                logger.info(
                    f"LLM generation successful: {response.output_tokens} tokens, "
                    f"{latency_ms:.0f}ms, ${response.cost_usd:.4f}"
                )
                
                return response
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM generation failed (attempt {attempt + 1}): {e}"
                )
                
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)
        
        # All retries exhausted
        raise LLMGenerationError(
            f"Failed after {self.config.max_retries} attempts: {last_error}"
        )
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Uses tiktoken for approximation. Actual tokens may vary by provider.
        """
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            # Fallback: rough estimation (1 token ~= 4 characters)
            return len(text) // 4


class ClaudeClient(LLMClient):
    """Anthropic Claude 3.5 Sonnet client implementation."""
    
    def _setup_client(self):
        """Initialize Anthropic client."""
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.config.api_key)
            logger.info(f"Claude client initialized: {self.model_config.model_name}")
        except ImportError:
            raise ImportError(
                "Anthropic SDK not installed. Run: pip install anthropic"
            )
    
    def _generate_impl(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate using Claude API."""
        
        # Build messages
        messages = [
            {"role": "user", "content": user_prompt}
        ]
        
        # API call
        response = self.client.messages.create(
            model=self.model_config.model_name,
            max_tokens=self.model_config.max_tokens,
            temperature=self.model_config.temperature,
            system=system_prompt,
            messages=messages,
            **self.model_config.extra_params,
            **kwargs
        )
        
        # Extract response
        content = response.content[0].text
        
        # Calculate cost
        cost = self.config.estimate_cost(
            response.usage.input_tokens,
            response.usage.output_tokens
        )
        
        return LLMResponse(
            content=content,
            model=self.model_config.model_name,
            provider=LLMProvider.CLAUDE,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            finish_reason=response.stop_reason,
            latency_ms=0.0,  # Set by caller
            cost_usd=cost,
            raw_response=response.model_dump()
        )


class JambaClient(LLMClient):
    """AI21 Jamba 1.5 Mini client implementation."""
    
    def _setup_client(self):
        """Initialize AI21 client."""
        try:
            from ai21 import AI21Client
            self.client = AI21Client(api_key=self.config.api_key)
            logger.info(f"Jamba client initialized: {self.model_config.model_name}")
        except ImportError:
            raise ImportError(
                "AI21 SDK not installed. Run: pip install ai21"
            )
    
    def _generate_impl(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate using Jamba API."""
        
        # Jamba uses chat format
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # API call
        response = self.client.chat.completions.create(
            model=self.model_config.model_name,
            messages=messages,
            max_tokens=self.model_config.max_tokens,
            temperature=self.model_config.temperature,
            **self.model_config.extra_params,
            **kwargs
        )
        
        # Extract response
        content = response.choices[0].message.content
        
        # Token usage (Jamba provides this)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        # Calculate cost
        cost = self.config.estimate_cost(input_tokens, output_tokens)
        
        return LLMResponse(
            content=content,
            model=self.model_config.model_name,
            provider=LLMProvider.JAMBA,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            finish_reason=response.choices[0].finish_reason,
            latency_ms=0.0,
            cost_usd=cost,
            raw_response=response.model_dump()
        )


class OpenAIClient(LLMClient):
    """OpenAI GPT-4 client implementation."""
    
    def _setup_client(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.config.api_key)
            logger.info(f"OpenAI client initialized: {self.model_config.model_name}")
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed. Run: pip install openai"
            )
    
    def _generate_impl(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate using OpenAI API."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # API call
        response = self.client.chat.completions.create(
            model=self.model_config.model_name,
            messages=messages,
            max_tokens=self.model_config.max_tokens,
            temperature=self.model_config.temperature,
            **self.model_config.extra_params,
            **kwargs
        )
        
        # Extract response
        content = response.choices[0].message.content
        
        # Token usage
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        # Calculate cost
        cost = self.config.estimate_cost(input_tokens, output_tokens)
        
        return LLMResponse(
            content=content,
            model=self.model_config.model_name,
            provider=LLMProvider.OPENAI,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            finish_reason=response.choices[0].finish_reason,
            latency_ms=0.0,
            cost_usd=cost,
            raw_response=response.model_dump_json()
        )


class GeminiClient(LLMClient):
    """Google Gemini client for large context reasoning."""
    
    def _setup_client(self):
        """Initialize Gemini client."""
        try:
            import google.generativeai as genai
            
            if not self.config.api_key:
                raise ValueError("GOOGLE_API_KEY not set")
            
            genai.configure(api_key=self.config.api_key)
            
            # Create model
            self.client = genai.GenerativeModel(model_name=self.model_config.model_name)
            
            logger.info(f"Gemini client initialized: {self.model_config.model_name}")
            logger.info(f"Context window: {self.model_config.context_window:,} tokens")
            
        except ImportError:
            raise ImportError(
                "Google Generative AI SDK not installed. Run: pip install google-generativeai"
            )
    
    def _generate_impl(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate using Gemini API."""
        
        # Gemini uses a single prompt (system + user combined)
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Build generation config
        generation_config = {
            "temperature": self.model_config.temperature,
            "max_output_tokens": self.model_config.max_tokens,
        }
        
        if self.model_config.supports_json_mode:
            generation_config["response_mime_type"] = "application/json"
        
        # API call
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        # Extract response
        content = response.text
        
        # Token usage (Gemini provides usage metadata)
        try:
            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count
        except AttributeError:
            # Fallback token estimation if not provided
            input_tokens = int(len(full_prompt.split()) * 1.3)
            output_tokens = int(len(content.split()) * 1.3)
        
        # Calculate cost
        cost = self.config.estimate_cost(input_tokens, output_tokens)
        
        return LLMResponse(
            content=content,
            model=self.model_config.model_name,
            provider=LLMProvider.GEMINI,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            finish_reason="stop",
            latency_ms=0.0,
            cost_usd=cost,
            raw_response=None
        )


class MockClient(LLMClient):
    """Mock LLM client for testing without API calls."""
    
    def _setup_client(self):
        """No actual client needed for mock."""
        logger.info("Mock LLM client initialized (testing mode)")


class LMStudioClient(LLMClient):
    """
    LM Studio local LLM client.
    
    Supports any model loaded in LM Studio via OpenAI-compatible API.
    Perfect for testing with DeepSeek-R1, Qwen, or other local models.
    """
    
    def _setup_client(self):
        """Initialize LM Studio client (uses OpenAI SDK)."""
        try:
            from openai import OpenAI
            
            # LM Studio default endpoint
            base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
            
            self.client = OpenAI(
                api_key="lm-studio",  # LM Studio doesn't need a real key
                base_url=base_url
            )
            
            logger.info(f"LM Studio client initialized at {base_url}")
            logger.info(f"Model: {self.model_config.model_name}")
            
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed. Run: pip install openai"
            )
    
    def _generate_impl(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate using LM Studio API."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # API call (OpenAI-compatible)
        response = self.client.chat.completions.create(
            model=self.model_config.model_name,  # Must match model loaded in LM Studio
            messages=messages,
            max_tokens=self.model_config.max_tokens,
            temperature=self.model_config.temperature,
            **self.model_config.extra_params,
            **kwargs
        )
        
        # Extract response
        content = response.choices[0].message.content
        
        # Token usage
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        
        # No cost for local models
        cost = 0.0
        
        return LLMResponse(
            content=content,
            model=self.model_config.model_name,
            provider=LLMProvider.LMSTUDIO,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            finish_reason=response.choices[0].finish_reason,
            latency_ms=0.0,
            cost_usd=cost,
            raw_response=response.model_dump_json()
        )


class MockClient(LLMClient):
    """Mock LLM client for testing without API calls."""
    
    def _setup_client(self):
        """No actual client needed for mock."""
        logger.info("Mock LLM client initialized (testing mode)")
    
    def _generate_impl(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Return mock response."""
        
        # Generate a simple mock refactor plan
        mock_plan = {
            "plan_id": "mock_001",
            "description": "Mock refactor plan for testing",
            "primary_changes": [
                {
                    "target_file": "test.py",
                    "operation": "modify",
                    "change_type": "function",
                    "start_line": 1,
                    "end_line": 10
                }
            ],
            "execution_order": [0],
            "risk_level": "low",
            "estimated_files_affected": 1
        }
        
        content = json.dumps(mock_plan, indent=2)
        
        return LLMResponse(
            content=content,
            model="mock-llm",
            provider=LLMProvider.MOCK,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            finish_reason="stop",
            latency_ms=0.0,
            cost_usd=0.0
        )


class LMStudioClient(LLMClient):
    """
    LM Studio client for local model inference.
    
    LM Studio runs a local OpenAI-compatible API server at http://localhost:1234
    Supports models like DeepSeek-R1, Qwen3, Gemma3, etc.
    """
    
    def _setup_client(self):
        """Initialize LM Studio client (OpenAI-compatible)."""
        try:
            from openai import OpenAI
            
            # LM Studio runs on localhost:1234 by default
            base_url = "http://localhost:1234/v1"
            
            self.client = OpenAI(
                api_key="lm-studio",  # LM Studio doesn't need real API key
                base_url=base_url
            )
            
            logger.info(f"LM Studio client initialized: {base_url}")
            logger.info(f"Model: {self.model_config.model_name}")
            
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed. Run: pip install openai"
            )
    
    def _generate_impl(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate using LM Studio API."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # API call to LM Studio
            response = self.client.chat.completions.create(
                model=self.model_config.model_name,
                messages=messages,
                max_tokens=self.model_config.max_tokens,
                temperature=self.model_config.temperature,
                **self.model_config.extra_params,
                **kwargs
            )
            
            # Extract response
            content = response.choices[0].message.content
            
            # Token usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            # Cost is $0 for local inference
            cost = 0.0
            
            return LLMResponse(
                content=content,
                model=self.model_config.model_name,
                provider=LLMProvider.LMSTUDIO,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                finish_reason=response.choices[0].finish_reason,
                latency_ms=0.0,
                cost_usd=cost,
                raw_response=response.model_dump_json()
            )
            
        except Exception as e:
            # Provide helpful error message for common issues
            error_msg = str(e)
            
            if "Connection" in error_msg or "refused" in error_msg:
                raise ConnectionError(
                    "Cannot connect to LM Studio. Please ensure:\n"
                    "1. LM Studio is running\n"
                    "2. A model is loaded\n"
                    "3. Local Server is started (green light in LM Studio)\n"
                    "4. Server is running on http://localhost:1234"
                )
            elif "model" in error_msg.lower():
                raise ValueError(
                    f"Model '{self.model_config.model_name}' not found in LM Studio.\n"
                    f"Available models: Check LM Studio's loaded models.\n"
                    f"Tip: Use the exact model name from LM Studio"
                )
            else:
                raise


class LLMClientFactory:
    """Factory for creating LLM clients based on provider."""
    
    @staticmethod
    def create(config: ReasonerConfig) -> LLMClient:
        """
        Create appropriate LLM client based on configuration.
        
        Args:
            config: Reasoner configuration
        
        Returns:
            LLMClient instance for the specified provider
        
        Raises:
            ValueError: If provider is not supported
        """
        
        clients = {
            LLMProvider.CLAUDE: ClaudeClient,
            LLMProvider.JAMBA: JambaClient,
            LLMProvider.OPENAI: OpenAIClient,
            LLMProvider.GEMINI: GeminiClient,
            LLMProvider.LMSTUDIO: LMStudioClient,
            LLMProvider.MOCK: MockClient,
        }
        
        client_class = clients.get(config.provider)
        if not client_class:
            raise ValueError(f"Unsupported provider: {config.provider}")
        
        return client_class(config)


class LLMGenerationError(Exception):
    """Raised when LLM generation fails after all retries."""
    pass
