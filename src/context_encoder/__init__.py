"""
Phase 3: Context Encoder (Mamba Layer)
========================================

The Context Encoder is responsible for compressing large codebases into
dense, lossy-less representations using State Space Models (Mamba-2).

This module provides:
- Integration with AI21 Jamba-1.5-Mini (Hybrid Mamba-Transformer)
- Context compression from GraphRAG subgraphs
- Integrity validation of compressed context
- Support for 256k token context windows

Architecture:
    GraphRAG Subgraph → Jamba-1.5-Mini → Compressed Context Block → Builder
"""

from .config import ContextEncoderConfig, JambaConfig, EncoderProvider
from .encoder import ContextEncoder
from .validator import ContextIntegrityValidator

__all__ = [
    "ContextEncoder",
    "ContextEncoderConfig",
    "EncoderProvider",
    "JambaConfig",
    "ContextIntegrityValidator",
]

__version__ = "0.1.0"
__phase__ = "Phase 3: The Context Encoder (Mamba Layer)"
