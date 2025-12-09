"""
Configuration for Phase 3 Context Encoder
==========================================

Manages settings for Jamba-1.5-Mini and context compression.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EncoderProvider(Enum):
    """Supported context encoder providers."""
    JAMBA_CLOUD = "jamba_cloud"  # AI21 Cloud API (recommended for production)
    JAMBA_LOCAL = "jamba_local"  # LM Studio local inference
    MOCK = "mock"                # Mock encoder for testing


@dataclass
class JambaConfig:
    """Configuration for AI21 Jamba-1.5-Mini model."""
    
    # Model Configuration
    model_name: str = "jamba-mini"  # AI21 model name (jamba-mini or jamba-large)
    context_window: int = 256_000  # 256k tokens
    max_output_tokens: int = 4096  # For context summary
    temperature: float = 0.3  # Low temperature for deterministic summaries
    
    # API Configuration (Cloud vs Local)
    use_cloud: bool = True  # True: AI21 Cloud, False: LM Studio local
    
    # AI21 Cloud Configuration
    cloud_api_url: str = "https://api.ai21.com/studio/v1"
    cloud_api_key: Optional[str] = None  # Set via AI21_API_KEY env var
    
    # LM Studio Local Configuration
    local_base_url: str = "http://localhost:1234/v1"  # LM Studio default
    local_api_key: Optional[str] = None  # Not needed for local
    
    # Common Configuration
    timeout: int = 300  # 5 minutes for large context
    batch_size: int = 1
    use_streaming: bool = False
    
    def __post_init__(self):
        """Validate configuration and load from environment."""
        if self.max_output_tokens > self.context_window:
            raise ValueError(
                f"max_output_tokens ({self.max_output_tokens}) cannot exceed "
                f"context_window ({self.context_window})"
            )
        
        # Load API key from environment if not set
        if self.use_cloud and not self.cloud_api_key:
            import os
            self.cloud_api_key = os.getenv("AI21_API_KEY")
    
    @property
    def base_url(self) -> str:
        """Get the active base URL based on cloud/local mode."""
        return self.cloud_api_url if self.use_cloud else self.local_base_url
    
    @property
    def api_key(self) -> Optional[str]:
        """Get the active API key based on cloud/local mode."""
        return self.cloud_api_key if self.use_cloud else self.local_api_key


@dataclass
class ContextEncoderConfig:
    """Main configuration for the Context Encoder."""
    
    provider: EncoderProvider = EncoderProvider.JAMBA_CLOUD
    jamba: JambaConfig = field(default_factory=JambaConfig)
    
    # Context Compression Settings
    compression_strategy: str = "technical_summary"  # or "pseudo_code"
    include_signatures: bool = True
    include_dependencies: bool = True
    include_comments: bool = False
    
    # Integrity Validation
    min_summary_length: int = 100  # Minimum characters in summary
    require_file_references: bool = True
    max_hallucination_score: float = 0.3  # TODO: Implement scoring
    
    # Provenance Metadata
    model_version: str = "jamba-1.5-mini"
    enable_checksum: bool = True
    log_context_stats: bool = True


# Global configuration instance
_config: Optional[ContextEncoderConfig] = None


def get_config() -> ContextEncoderConfig:
    """Get the global context encoder configuration."""
    global _config
    if _config is None:
        _config = ContextEncoderConfig()
    return _config


def set_config(config: ContextEncoderConfig) -> None:
    """Set the global context encoder configuration."""
    global _config
    _config = config
