"""
Configuration management for Phase 2 Reasoner.

Handles LLM provider selection, API keys, model parameters, and cost optimization.
Follows the "Frankenstein" architecture principle - mix providers based on task complexity.
"""

import os
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


class LLMProvider(str, Enum):
    """Supported LLM providers for The Reasoner."""
    
    # Primary: Best for complex reasoning with strict JSON schema adherence
    CLAUDE = "claude"
    
    # Fallback: Cost-effective for simpler refactors with massive context
    JAMBA = "jamba"
    
    # Alternative: Reliable general-purpose option
    OPENAI = "openai"
    
    # Google: Gemini models with large context and competitive pricing
    GEMINI = "gemini"
    
    # Local LLM via LM Studio (DeepSeek-R1, Qwen, etc.)
    LMSTUDIO = "lmstudio"
    
    # Mock: For testing without API costs
    MOCK = "mock"


@dataclass
class ModelConfig:
    """Configuration for a specific LLM model."""
    
    model_name: str
    max_tokens: int
    temperature: float = 0.1  # Low temp for deterministic refactor plans
    context_window: int = 200_000
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    supports_json_mode: bool = False
    
    # Provider-specific settings
    extra_params: Dict[str, Any] = field(default_factory=dict)


# Model configurations aligned with White Paper specifications
CLAUDE_CONFIG = ModelConfig(
    model_name="claude-3-5-sonnet-20241022",
    max_tokens=8192,
    temperature=0.1,
    context_window=200_000,
    cost_per_1k_input=0.003,  # $3/M tokens
    cost_per_1k_output=0.015,  # $15/M tokens
    supports_json_mode=True,
    extra_params={
        "top_p": 0.9,
        "stop_sequences": ["</refactor_plan>"],
    }
)

JAMBA_CONFIG = ModelConfig(
    model_name="jamba-1.5-mini",
    max_tokens=4096,
    temperature=0.1,
    context_window=256_000,  # Mamba-2 hybrid architecture
    cost_per_1k_input=0.0002,  # $0.2/M tokens (15x cheaper than Claude)
    cost_per_1k_output=0.0004,  # $0.4/M tokens
    supports_json_mode=False,
    extra_params={
        "top_p": 0.95,
    }
)

OPENAI_CONFIG = ModelConfig(
    model_name="gpt-4o-2024-11-20",
    max_tokens=16384,
    temperature=0.1,
    context_window=128_000,
    cost_per_1k_input=0.0025,  # $2.5/M tokens
    cost_per_1k_output=0.01,  # $10/M tokens
    supports_json_mode=True,
    extra_params={
        "response_format": {"type": "json_object"},
    }
)

GEMINI_CONFIG = ModelConfig(
    model_name="gemini-2.5-flash",  # Gemini 2.5 Flash (latest, fast & efficient)
    max_tokens=8192,
    temperature=0.1,
    context_window=1_000_000,  # 1M tokens context window
    cost_per_1k_input=0.000075,  # $0.075/M input (extremely cheap!)
    cost_per_1k_output=0.0003,   # $0.30/M output (98% cheaper than Claude!)
    supports_json_mode=True,
    extra_params={}
)

LMSTUDIO_CONFIG = ModelConfig(
    model_name="qwen3-8b",  # Or qwen3-8b, gemma-3-4b
    max_tokens=8192,
    temperature=0.1,
    context_window=32_000,  # Adjust based on your loaded model
    cost_per_1k_input=0.0,  # FREE - runs locally
    cost_per_1k_output=0.0,  # FREE
    supports_json_mode=False,  # Most local models support JSON
    extra_params={
        "top_p": 0.9,
    }
)

MOCK_CONFIG = ModelConfig(
    model_name="mock-llm",
    max_tokens=4096,
    temperature=0.0,
    context_window=100_000,
    cost_per_1k_input=0.0,
    cost_per_1k_output=0.0,
    supports_json_mode=True,
)


@dataclass
class ReasonerConfig:
    """
    Main configuration for The Reasoner.
    
    Attributes:
        provider: Which LLM provider to use (default: Claude for best reasoning)
        fallback_provider: Backup provider if primary fails
        api_key: API key for the provider (falls back to env vars)
        model_config: Model-specific configuration
        max_retries: Number of retry attempts for failed requests
        retry_delay: Delay between retries in seconds
        enable_caching: Use provider-specific caching (Claude prompt caching)
        output_format: Preferred output format ("json" or "xml")
    """
    
    provider: LLMProvider = LLMProvider.CLAUDE
    fallback_provider: Optional[LLMProvider] = LLMProvider.JAMBA
    
    # API Keys (will check environment variables)
    api_key: Optional[str] = None
    fallback_api_key: Optional[str] = None
    
    # Model configuration
    model_config: Optional[ModelConfig] = None
    
    # Retry and reliability settings
    max_retries: int = 3
    retry_delay: float = 2.0
    timeout: int = 120  # seconds
    
    # Performance optimization
    enable_caching: bool = True  # Claude prompt caching saves costs
    stream_response: bool = False  # Streaming for real-time feedback
    
    # Output preferences
    output_format: str = "json"  # "json" or "xml"
    validate_output: bool = True  # Run Pydantic validation
    
    def __post_init__(self):
        """Initialize model config and API keys after dataclass creation."""
        # Set model_config if not provided
        if self.model_config is None:
            self.model_config = self._get_default_model_config(self.provider)
        
        # Set API keys from environment if not provided
        if self.api_key is None:
            self.api_key = self._get_api_key_for_provider(self.provider)
        
        if self.fallback_api_key is None and self.fallback_provider:
            self.fallback_api_key = self._get_api_key_for_provider(self.fallback_provider)
    
    def _get_api_key_for_provider(self, provider: LLMProvider) -> Optional[str]:
        """Get API key from environment variables."""
        env_vars = {
            LLMProvider.CLAUDE: "ANTHROPIC_API_KEY",
            LLMProvider.JAMBA: "AI21_API_KEY",
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.GEMINI: "GEMINI_API_KEY",  # Also checks GOOGLE_API_KEY as fallback
            LLMProvider.LMSTUDIO: None,  # No API key needed
            LLMProvider.MOCK: None,
        }
        
        env_var = env_vars.get(provider)
        if env_var:
            # For Gemini, try both GEMINI_API_KEY and GOOGLE_API_KEY
            if provider == LLMProvider.GEMINI:
                return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            return os.getenv(env_var)
        return None
    
    def _get_default_model_config(self, provider: LLMProvider) -> ModelConfig:
        """Get default model configuration for provider."""
        configs = {
            LLMProvider.CLAUDE: CLAUDE_CONFIG,
            LLMProvider.JAMBA: JAMBA_CONFIG,
            LLMProvider.OPENAI: OPENAI_CONFIG,
            LLMProvider.GEMINI: GEMINI_CONFIG,
            LLMProvider.LMSTUDIO: LMSTUDIO_CONFIG,
            LLMProvider.MOCK: MOCK_CONFIG,
        }
        return configs[provider]
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API cost for a given request."""
        if not self.model_config:
            return 0.0
        
        input_cost = (input_tokens / 1000) * self.model_config.cost_per_1k_input
        output_cost = (output_tokens / 1000) * self.model_config.cost_per_1k_output
        
        return input_cost + output_cost
    
    def should_use_fallback(self, estimated_tokens: int) -> bool:
        """
        Decide if fallback provider should be used based on cost optimization.
        
        For simple tasks with large context, Jamba is 15x cheaper than Claude.
        """
        if not self.fallback_provider:
            return False
        
        # Use Jamba for large contexts where cost matters more than reasoning quality
        if self.fallback_provider == LLMProvider.JAMBA and estimated_tokens > 50_000:
            return True
        
        return False

def load_config_from_env() -> ReasonerConfig:
    """
    Load configuration from environment variables.
    
    Environment Variables:
        REASONER_PROVIDER: Primary LLM provider (claude|jamba|openai|lmstudio)
        REASONER_FALLBACK: Fallback provider
        ANTHROPIC_API_KEY: Claude API key
        AI21_API_KEY: Jamba API key
        OPENAI_API_KEY: OpenAI API key
        LMSTUDIO_BASE_URL: LM Studio API endpoint (default: http://localhost:1234/v1)
        REASONER_MAX_RETRIES: Maximum retry attempts
        REASONER_ENABLE_CACHING: Enable prompt caching (true|false)
    """
    
    provider_str = os.getenv("REASONER_PROVIDER", "claude").lower()
    fallback_str = os.getenv("REASONER_FALLBACK", "jamba").lower()
    
    provider = LLMProvider(provider_str)
    fallback = LLMProvider(fallback_str) if fallback_str else None
    
    return ReasonerConfig(
        provider=provider,
        fallback_provider=fallback,
        max_retries=int(os.getenv("REASONER_MAX_RETRIES", "3")),
        enable_caching=os.getenv("REASONER_ENABLE_CACHING", "true").lower() == "true",
    )
