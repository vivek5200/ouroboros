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
    JAMBA = "jamba"  # AI21 Jamba-1.5-Mini (Hybrid Mamba-Transformer)
    MOCK = "mock"    # Mock encoder for testing


@dataclass
class JambaConfig:
    """Configuration for AI21 Jamba-1.5-Mini model."""
    
    model_name: str = "ai21/jamba-1.5-mini"
    context_window: int = 256_000  # 256k tokens
    max_output_tokens: int = 4096  # For context summary
    temperature: float = 0.3  # Low temperature for deterministic summaries
    
    # API Configuration
    base_url: str = "http://localhost:1234/v1"  # LM Studio default
    api_key: Optional[str] = None
    timeout: int = 300  # 5 minutes for large context
    
    # Performance
    batch_size: int = 1
    use_streaming: bool = False
    
    def __post_init__(self):
        """Validate configuration."""
        if self.max_output_tokens > self.context_window:
            raise ValueError(
                f"max_output_tokens ({self.max_output_tokens}) cannot exceed "
                f"context_window ({self.context_window})"
            )


@dataclass
class ContextEncoderConfig:
    """Main configuration for the Context Encoder."""
    
    provider: EncoderProvider = EncoderProvider.JAMBA
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
