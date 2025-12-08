"""
Phase 2: The Reasoner - LLM-powered refactoring intelligence.

This module implements the reasoning layer that generates validated refactor plans
using context from Phase 1 (The Librarian). It supports multiple LLM providers
with Claude 3.5 Sonnet as the primary model for complex reasoning and AI21 Jamba
as a cost-effective fallback for simpler operations.

Architecture Components:
- config.py: Provider configuration and API key management
- llm_client.py: Abstract LLM interface with provider implementations
- prompt_builder.py: Context-aware prompt engineering
- plan_parser.py: LLM output to Pydantic RefactorPlan validation
- reasoner.py: Main orchestrator for refactor plan generation
- dependency_analyzer.py: Graph-based impact analysis

Usage:
    from src.reasoner import Reasoner
    from src.reasoner.config import ReasonerConfig
    
    config = ReasonerConfig(provider="claude")  # or "jamba", "openai"
    reasoner = Reasoner(config)
    
    plan = reasoner.generate_refactor_plan(
        task="Rename function foo to bar",
        target_file="src/module.py"
    )
"""

from .config import ReasonerConfig, LLMProvider
from .reasoner import Reasoner

__all__ = [
    "ReasonerConfig",
    "LLMProvider",
    "Reasoner",
]

__version__ = "2.0.0"
