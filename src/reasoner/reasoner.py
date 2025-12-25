"""
Main Reasoner orchestrator for Phase 2.

Coordinates the entire refactor plan generation pipeline:
1. Retrieve context from Neo4j graph
2. Serialize context for LLM consumption
3. Generate prompts and query LLM
4. Parse and validate RefactorPlan
5. Perform dependency impact analysis
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from .config import ReasonerConfig, load_config_from_env
from .llm_client import LLMClientFactory, LLMClient, LLMResponse
from .prompt_builder import PromptBuilder
from .plan_parser import PlanParser, PlanValidator
from .dependency_analyzer import DependencyAnalyzer

from src.librarian.graph_db import OuroborosGraphDB
from src.librarian.retriever import GraphRetriever
from src.librarian.context_serializer import ContextSerializer, CompressedContextBlock
from src.architect.schemas import RefactorPlan, ValidationResult
from src.context_encoder import ContextEncoder


logger = logging.getLogger(__name__)


class Reasoner:
    """
    Phase 2: The Reasoner - Main orchestrator.
    
    Generates validated refactor plans using LLM reasoning combined with
    graph-based dependency analysis.
    
    Usage:
        config = ReasonerConfig(provider="claude")
        reasoner = Reasoner(config)
        
        plan = reasoner.generate_refactor_plan(
            task="Rename function foo to bar",
            target_file="src/module.py"
        )
    """
    
    def __init__(self, config: Optional[ReasonerConfig] = None):
        """
        Initialize Reasoner.
        
        Args:
            config: Configuration (loads from env if None)
        """
        self.config = config or load_config_from_env()
        
        # Initialize components
        self.llm_client: LLMClient = LLMClientFactory.create(self.config)
        self.prompt_builder = PromptBuilder(include_examples=True)
        self.plan_parser = PlanParser(strict_validation=False)
        self.plan_validator = PlanValidator()
        
        # Database connections
        self.db = OuroborosGraphDB()
        self.retriever = GraphRetriever(self.db)
        
        # Context handling (Phase 2: Serializer, Phase 3: Encoder)
        self.serializer = ContextSerializer(format="markdown")
        try:
            self.encoder = ContextEncoder()
        except Exception as e:
            logger.warning(f"ContextEncoder init failed (skipping deep context): {e}")
            self.encoder = None
        
        self.dependency_analyzer = DependencyAnalyzer(self.db)
        
        logger.info(f"Reasoner initialized with provider: {self.config.provider}")
    
    def generate_refactor_plan(
        self,
        task_description: str,
        target_file: Optional[str] = None,
        target_symbol: Optional[str] = None,
        context_files: Optional[List[str]] = None,
        max_context_tokens: int = 100_000,
        use_deep_context: bool = False,
    ) -> RefactorPlan:
        """
        Generate a validated refactor plan for the given task.
        
        Args:
            task_description: What the user wants to accomplish
            target_file: Primary file to refactor (optional)
            target_symbol: Specific symbol to refactor (optional)
            context_files: Additional files to include in context
            max_context_tokens: Maximum tokens for context (respects LLM limits)
            use_deep_context: Use Phase 3 Jamba encoder for massive context (200k+ tokens)
        
        Returns:
            Validated RefactorPlan
        
        Raises:
            ReasonerError: If plan generation or validation fails
        """
        
        logger.info(f"Generating refactor plan: {task_description}")
        
        # Step 1: Retrieve context from graph
        context_blocks = self._retrieve_context(
            target_file=target_file,
            context_files=context_files,
            max_tokens=max_context_tokens,
            use_deep_context=use_deep_context
        )
        
        if not context_blocks:
            raise ReasonerError("No context available - graph may be empty")
        
        logger.info(f"Retrieved {len(context_blocks)} context blocks")
        
        # Step 2: Perform dependency analysis
        dependency_info = None
        if target_file and target_symbol:
            dependency_info = self._analyze_dependencies(target_file, target_symbol)
            logger.info(f"Dependency analysis: {dependency_info.get('estimated_impact', 0)} files affected")
        
        # Step 3: Build prompts
        operation_type = self._infer_operation_type(task_description)
        system_prompt = self.prompt_builder.build_system_prompt(operation_type)
        user_prompt = self.prompt_builder.build_user_prompt(
            task_description=task_description,
            context_blocks=context_blocks,
            dependency_info=dependency_info
        )
        
        # Estimate tokens
        prompt_tokens = self.prompt_builder.estimate_prompt_tokens(system_prompt, user_prompt)
        logger.info(f"Prompt size: {prompt_tokens} tokens")
        
        # Check if we should use fallback provider (cost optimization)
        if self.config.should_use_fallback(prompt_tokens):
            logger.info("Using fallback provider for cost optimization")
            self._switch_to_fallback()
        
        # Step 4: Generate with LLM
        try:
            llm_response = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            logger.info(
                f"LLM generation complete: {llm_response.output_tokens} tokens, "
                f"${llm_response.cost_usd:.4f}"
            )
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            
            # Try fallback provider if available
            if self.config.fallback_provider and not self._is_using_fallback():
                logger.info("Attempting with fallback provider")
                self._switch_to_fallback()
                
                llm_response = self.llm_client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt
                )
            else:
                raise ReasonerError(f"LLM generation failed: {e}")
        
        # Step 5: Parse and validate
        plan, validation = self.plan_parser.parse(llm_response.content)
        
        if not plan:
            logger.error(f"Plan parsing failed: {validation.errors}")
            raise ReasonerError(
                f"Failed to parse RefactorPlan: {', '.join(validation.errors)}"
            )
        
        # Additional validation
        validation = self.plan_validator.validate_plan(plan)
        
        if not validation.is_valid:
            logger.error(f"Plan validation failed: {validation.errors}")
            raise ReasonerError(
                f"Invalid RefactorPlan: {', '.join(validation.errors)}"
            )
        
        if validation.warnings:
            logger.warning(f"Plan warnings: {', '.join(validation.warnings)}")
        
        logger.info(f"RefactorPlan generated successfully: {plan.plan_id}")
        
        return plan
    
    def _retrieve_context(
        self,
        target_file: Optional[str],
        context_files: Optional[List[str]],
        max_tokens: int,
        use_deep_context: bool = False
    ) -> List[CompressedContextBlock]:
        """
        Retrieve and serialize context from graph.
        
        Uses either:
        - Phase 2: ContextSerializer (markdown, fast, <50k tokens)
        - Phase 3: ContextEncoder (Jamba compression, 200k+ tokens)
        """
        
        context_blocks = []
        total_tokens = 0
        
        # Get target file context
        if target_file:
            context = self.retriever.get_file_context(target_file)
            if context:
                if use_deep_context:
                    # Phase 3: Use Jamba for deep compression
                    raw_content = self._context_to_raw_string(context)
                    compressed = self.encoder.compress(
                        codebase_context=raw_content,
                        target_files=[target_file],
                        metadata={"task": "retrieve_context"}
                    )
                    # Wrap in CompressedContextBlock for compatibility
                    block = CompressedContextBlock(
                        block_id=f"deep_{target_file}",
                        block_type="file",
                        content=compressed.summary,
                        format="markdown",
                        token_count=compressed.tokens_out
                    )
                    logger.info(
                        f"Deep context compression: {compressed.tokens_in} → "
                        f"{compressed.tokens_out} tokens (ratio: {compressed.compression_ratio:.1f}x)"
                    )
                else:
                    # Phase 2: Use fast markdown serializer
                    block = self.serializer.serialize_file_context(context)
                
                context_blocks.append(block)
                total_tokens += block.token_count
        
        # Get additional context files
        if context_files:
            for file_path in context_files:
                if total_tokens >= max_tokens:
                    logger.warning(f"Context token limit reached ({max_tokens})")
                    break
                
                context = self.retriever.get_file_context(file_path)
                if context:
                    block = self.serializer.serialize_file_context(context)
                    context_blocks.append(block)
                    total_tokens += block.token_count
        
        # If no specific files, get sample from graph
        if not context_blocks:
            files_summary = self.retriever.get_all_files_summary()
            
            for file_info in files_summary[:5]:  # Limit to 5 files
                if total_tokens >= max_tokens:
                    break
                
                context = self.retriever.get_file_context(file_info['path'])
                if context:
                    block = self.serializer.serialize_file_context(context)
                    context_blocks.append(block)
                    total_tokens += block.token_count
        
        return context_blocks
    
    def _analyze_dependencies(
        self,
        target_file: str,
        target_symbol: str
    ) -> Dict[str, Any]:
        """Perform dependency impact analysis."""
        
        # Try function rename analysis first
        dep_info = self.dependency_analyzer.analyze_function_rename(
            target_file,
            target_symbol
        )
        
        # If no results, try class rename
        if dep_info.get("estimated_impact", 0) == 0:
            dep_info = self.dependency_analyzer.analyze_class_rename(
                target_file,
                target_symbol
            )
        
        return dep_info
    
    def _infer_operation_type(self, task_description: str) -> Optional[str]:
        """Infer operation type from task description."""
        
        task_lower = task_description.lower()
        
        if "rename" in task_lower:
            return "rename"
        elif "extract" in task_lower:
            return "extract"
        elif "move" in task_lower:
            return "move"
        elif "delete" in task_lower or "remove" in task_lower:
            return "delete"
        
        return None
    
    def _switch_to_fallback(self):
        """Switch to fallback LLM provider."""
        if not self.config.fallback_provider:
            return
        
        logger.info(f"Switching to fallback provider: {self.config.fallback_provider}")
        
        # Create new config with fallback as primary
        fallback_config = ReasonerConfig(
            provider=self.config.fallback_provider,
            api_key=self.config.fallback_api_key,
            max_retries=self.config.max_retries,
            retry_delay=self.config.retry_delay,
        )
        
        self.llm_client = LLMClientFactory.create(fallback_config)
        self.config = fallback_config
    
    def _is_using_fallback(self) -> bool:
        """Check if currently using fallback provider."""
        return self.config.provider == self.config.fallback_provider
    
    def _context_to_raw_string(self, context: Dict[str, Any]) -> str:
        """
        Convert graph context to raw string for Phase 3 encoding.
        
        Args:
            context: Context dict from GraphRetriever
        
        Returns:
            Raw string representation of the context
        """
        parts = []
        
        # Add file header
        if "file_path" in context:
            parts.append(f"# File: {context['file_path']}\n")
        
        # Add imports
        if "imports" in context and context["imports"]:
            parts.append("## Imports")
            for imp in context["imports"]:
                parts.append(f"- {imp}")
            parts.append("")
        
        # Add classes
        if "classes" in context:
            for cls in context["classes"]:
                parts.append(f"## Class: {cls.get('name', 'Unknown')}")
                if "methods" in cls:
                    for method in cls["methods"]:
                        parts.append(f"  - {method.get('name', 'unknown')}()")
                parts.append("")
        
        # Add functions
        if "functions" in context:
            parts.append("## Functions")
            for func in context["functions"]:
                parts.append(f"- {func.get('name', 'unknown')}()")
            parts.append("")
        
        # Add full content if available
        if "content" in context:
            parts.append("## Full Content")
            parts.append("```")
            parts.append(context["content"])
            parts.append("```")
        
        return "\n".join(parts)
    
    def estimate_cost(
        self,
        task_description: str,
        target_file: Optional[str] = None,
        context_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Estimate cost for generating a refactor plan.
        
        Args:
            task_description: Refactoring task
            target_file: Primary file
            context_files: Additional context files
        
        Returns:
            Dictionary with token estimates and cost
        """
        
        # Retrieve context (without LLM call)
        context_blocks = self._retrieve_context(target_file, context_files, 200_000)
        
        # Build prompts
        system_prompt = self.prompt_builder.build_system_prompt()
        user_prompt = self.prompt_builder.build_user_prompt(
            task_description=task_description,
            context_blocks=context_blocks
        )
        
        # Estimate tokens
        input_tokens = self.prompt_builder.estimate_prompt_tokens(system_prompt, user_prompt)
        output_tokens = 2000  # Estimated RefactorPlan size
        
        # Calculate cost
        cost = self.config.estimate_cost(input_tokens, output_tokens)
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost_usd": cost,
            "provider": self.config.provider.value,
            "model": self.config.model_config.model_name
        }
    
    def close(self):
        """Clean up resources."""
        if self.db:
            self.db.close()
        if self.dependency_analyzer:
            self.dependency_analyzer.close()


class ReasonerError(Exception):
    """Raised when Reasoner operations fail."""
    pass
