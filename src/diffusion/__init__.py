"""
Phase 4: Diffusion Layer (The Builder)
========================================

The Diffusion Layer generates code patches using discrete diffusion models
with AST-aware masking for deterministic token selection.

This module provides:
- Tree-Sitter AST-based masking for slot tokens
- Deterministic masking anchored to AST spans
- Discrete diffusion model with classifier-free guidance
- Noise scheduling (linear, cosine, sqrt)
- Autoregressive fallback for failed generations
- Integration with Qwen2.5-Coder backbone
"""

from .masking import ASTMasker, MaskingStrategy, MaskedSpan
from .config import (
    DiffusionConfig,
    DiffusionBackbone,
    NoiseSchedule,
    get_config,
    FAST_CONFIG,
    BALANCED_CONFIG,
    QUALITY_CONFIG,
    MOCK_CONFIG,
)
from .diffusion_model import (
    DiscreteDiffusionModel,
    NoiseScheduler,
    DiffusionSample,
)

__all__ = [
    # Masking
    "ASTMasker",
    "MaskingStrategy",
    "MaskedSpan",
    # Configuration
    "DiffusionConfig",
    "DiffusionBackbone",
    "NoiseSchedule",
    "get_config",
    "FAST_CONFIG",
    "BALANCED_CONFIG",
    "QUALITY_CONFIG",
    "MOCK_CONFIG",
    # Diffusion Model
    "DiscreteDiffusionModel",
    "NoiseScheduler",
    "DiffusionSample",
]

__version__ = "0.1.0"
__phase__ = "Phase 4: The Builder (Diffusion Layer)"
