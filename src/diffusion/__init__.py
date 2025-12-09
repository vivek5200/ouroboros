"""
Phase 4: Diffusion Layer (The Builder)
========================================

The Diffusion Layer generates code patches using discrete diffusion models
with AST-aware masking for deterministic token selection.

This module provides:
- Tree-Sitter AST-based masking for slot tokens
- Deterministic masking anchored to AST spans
- Integration with diffusion models for code generation
"""

from .masking import ASTMasker, MaskingStrategy, MaskedSpan

__all__ = [
    "ASTMasker",
    "MaskingStrategy",
    "MaskedSpan",
]

__version__ = "0.1.0"
__phase__ = "Phase 4: The Builder (Diffusion Layer)"
