"""
End-to-End Ouroboros Code Generation Pipeline

This module orchestrates the complete code generation workflow:
    Phase 1: The Librarian (Knowledge Graph) → OuroborosGraphDB
    Phase 2: The Reasoner (Analysis) → RefactorPlan
    Phase 3: The Compressor (Context) → CompressedContext via Jamba
    Phase 4: The Builder (Generation) → GeneratedPatch via Diffusion

Usage:
    from src.ouroboros_pipeline import OuroborosCodeGenerator
    
    # Initialize with graph database
    generator = OuroborosCodeGenerator(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password"
    )
    
    # Generate patches for an issue
    patches = generator.generate(
        issue_description="Optimize database queries in user service",
        target_files=["src/services/user_service.py"],
        config="balanced"
    )
    
    # Apply patches
    for patch in patches:
        if patch.can_apply() and patch.risk_score() < 0.3:
            generator.apply_patch(patch)

Created: 2025-12-10
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import json
from datetime import datetime

# Phase 1: Knowledge Graph
from src.librarian.graph_db import OuroborosGraphDB
from src.librarian.retriever import GraphRetriever

# Phase 2: Reasoner
from src.reasoner.dependency_analyzer import DependencyAnalyzer

# Phase 3: Context Encoder (Jamba)
from src.context_encoder import ContextEncoder, ContextEncoderConfig

# Phase 4: Builder (Diffusion)
from src.diffusion.builder import Builder, RefactorPlan, GeneratedPatch
from src.diffusion.config import (
    DiffusionConfig,
    FAST_CONFIG,
    BALANCED_CONFIG,
    QUALITY_CONFIG,
    MOCK_CONFIG,
)

# Phase 5: Safety and Provenance
from src.utils.provenance_logger import ProvenanceLogger

logger = logging.getLogger(__name__)


@dataclass
class GenerationRequest:
    """
    Request for code generation.
    
    Attributes:
        issue_description: High-level description of what to change
        target_files: List of files to potentially modify
        target_functions: Optional list of specific functions to refactor
        context_limit: Maximum context tokens for compression
        priority: Priority level (1-10, higher = more important)
        metadata: Additional metadata
    """
    issue_description: str
    target_files: List[Path]
    target_functions: Optional[List[str]] = None
    context_limit: int = 4096
    priority: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """
    Result of code generation.
    
    Attributes:
        patches: Generated patches
        refactor_plans: Original refactor plans from Reasoner
        compressed_contexts: Compressed contexts from Context Encoder
        success: Whether generation succeeded
        errors: List of errors encountered
        metadata: Generation metadata
    """
    patches: List[GeneratedPatch]
    refactor_plans: List[RefactorPlan]
    compressed_contexts: List[Dict[str, Any]]
    success: bool
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_applicable_patches(self, max_risk: float = 0.5) -> List[GeneratedPatch]:
        """Get patches that are safe to apply."""
        return [
            p for p in self.patches
            if p.can_apply() and p.risk_score() <= max_risk
        ]
    
    def get_high_risk_patches(self, threshold: float = 0.5) -> List[GeneratedPatch]:
        """Get patches that need manual review."""
        return [
            p for p in self.patches
            if p.risk_score() > threshold
        ]


class OuroborosCodeGenerator:
    """
    End-to-end code generation pipeline.
    
    Orchestrates:
    1. Phase 1: Knowledge graph retrieval (Librarian)
    2. Phase 2: Analysis and planning (Reasoner)
    3. Phase 3: Context compression (Jamba)
    4. Phase 4: Code generation (Builder/Diffusion)
    
    Usage:
        generator = OuroborosCodeGenerator(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            ai21_api_key="your_api_key"
        )
        
        result = generator.generate(
            issue_description="Optimize database queries",
            target_files=["src/services/user_service.py"],
            config="balanced"
        )
        
        # Apply safe patches
        for patch in result.get_applicable_patches(max_risk=0.3):
            generator.apply_patch(patch)
    """
    
    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        ai21_api_key: Optional[str] = None,
        diffusion_config: Optional[DiffusionConfig] = None,
        use_mock: bool = False,
        skip_db_init: bool = False,
    ):
        """
        Initialize Ouroboros pipeline.
        
        Args:
            neo4j_uri: Neo4j database URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            ai21_api_key: AI21 API key for Jamba (optional if use_mock=True)
            diffusion_config: Custom diffusion config (optional)
            use_mock: Use mock implementations for testing
            skip_db_init: Skip database initialization (for testing without Neo4j)
        """
        self.use_mock = use_mock
        
        # Phase 1: Initialize graph database
        logger.info("Initializing Phase 1: Knowledge Graph (Librarian)")
        if skip_db_init or use_mock:
            logger.warning("Skipping Neo4j initialization (mock/test mode)")
            # Create mock graph_db and retriever with proper return values
            from unittest.mock import Mock
            self.graph_db = Mock()
            self.graph_db.close = Mock()
            self.retriever = Mock()
            # Mock retriever methods to return proper data structures
            self.retriever.find_nodes = Mock(return_value=[
                {"id": "mock_file_1", "path": "mock_path", "language": "python"}
            ])
            self.retriever.get_nodes_by_property = Mock(return_value=[
                {"id": "mock_file_1", "path": "mock_path", "language": "python"}
            ])
            self.retriever.get_related_nodes = Mock(return_value=[
                {"id": "mock_func_1", "name": "mock_function", "start_line": 1, "end_line": 10}
            ])
            self.retriever.get_node_context = Mock(return_value={
                "dependencies": [],
                "callers": [],
                "imports": []
            })
        else:
            self.graph_db = OuroborosGraphDB(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password
            )
            self.retriever = GraphRetriever(self.graph_db)
        
        # Phase 2: Initialize reasoner components
        logger.info("Initializing Phase 2: Reasoner")
        if skip_db_init or use_mock:
            self.dependency_analyzer = Mock()
            # Mock dependency analyzer methods to return empty list
            self.dependency_analyzer.get_dependencies = Mock(return_value=[])
            self.dependency_analyzer.find_dependencies = Mock(return_value=[])
        else:
            self.dependency_analyzer = DependencyAnalyzer(self.graph_db)
        
        # Phase 3: Initialize Context Encoder (Jamba)
        logger.info("Initializing Phase 3: Context Encoder (Jamba)")
        if use_mock:
            logger.warning("Using MOCK mode - no real API calls")
            self.context_encoder = None
        else:
            if not ai21_api_key:
                logger.warning("No AI21 API key provided - some features may be limited")
            config = ContextEncoderConfig(api_key=ai21_api_key) if ai21_api_key else None
            self.context_encoder = ContextEncoder(config=config) if config else None
        
        # Phase 4: Initialize builder
        logger.info("Initializing Phase 4: Builder (Diffusion)")
        if use_mock:
            self.diffusion_config = MOCK_CONFIG
        else:
            self.diffusion_config = diffusion_config or BALANCED_CONFIG
        self.builder = Builder(config=self.diffusion_config)
        
        logger.info("Ouroboros pipeline initialized successfully")
    
    def generate(
        self,
        issue_description: str,
        target_files: Optional[List[str]] = None,
        target_functions: Optional[List[str]] = None,
        config: str = "balanced",
        context_limit: int = 4096,
        max_patches: int = 10,
    ) -> GenerationResult:
        """
        Generate code patches for an issue.
        
        This is the main entry point for end-to-end code generation.
        
        Args:
            issue_description: Description of what needs to be changed
            target_files: Files to potentially modify (optional)
            target_functions: Specific functions to refactor (optional)
            config: Diffusion config ("fast", "balanced", "quality", "mock")
            context_limit: Maximum context tokens
            max_patches: Maximum number of patches to generate
        
        Returns:
            GenerationResult with patches and metadata
        
        Example:
            result = generator.generate(
                issue_description="Add caching to user lookup functions",
                target_files=["src/services/user_service.py"],
                config="balanced"
            )
        """
        start_time = datetime.now()
        logger.info(f"Starting code generation: {issue_description}")
        
        # Initialize provenance logger
        provenance_logger = ProvenanceLogger(
            issue_description=issue_description,
            config={
                "diffusion_config": config,
                "context_limit": context_limit,
                "max_patches": max_patches,
            }
        )
        
        try:
            # Convert file paths
            target_paths = [Path(f) for f in target_files] if target_files else []
            
            # Create generation request
            request = GenerationRequest(
                issue_description=issue_description,
                target_files=target_paths,
                target_functions=target_functions,
                context_limit=context_limit,
                metadata={"config": config}
            )
            
            # Update builder config if needed
            if config != self.diffusion_config.backbone.value.lower():
                self._update_config(config)
            
            # Step 1: Analyze and plan (Phase 2)
            logger.info("Phase 2: Analyzing and creating refactor plans")
            plan_start = datetime.now()
            refactor_plans = self._create_refactor_plans(request)
            plan_duration = (datetime.now() - plan_start).total_seconds() * 1000
            
            # Log Phase 2 model usage (Reasoner)
            provenance_logger.log_model_usage(
                phase="reasoner",
                model_name="dependency-analyzer",
                purpose="analyzing dependencies and creating refactor plans",
                tokens_used=0,  # Internal analysis, no API calls
                duration_ms=plan_duration
            )
            
            if not refactor_plans:
                logger.warning("No refactor plans generated")
                return GenerationResult(
                    patches=[],
                    refactor_plans=[],
                    compressed_contexts=[],
                    success=False,
                    errors=["No refactor plans could be generated"],
                    metadata={"duration_seconds": (datetime.now() - start_time).total_seconds()}
                )
            
            logger.info(f"Generated {len(refactor_plans)} refactor plans")
            
            # Limit number of plans
            if len(refactor_plans) > max_patches:
                logger.info(f"Limiting to {max_patches} highest priority plans")
                refactor_plans = sorted(
                    refactor_plans,
                    key=lambda p: p.priority,
                    reverse=True
                )[:max_patches]
            
            # Step 2: Compress context (Phase 3)
            logger.info("Phase 3: Compressing context with Jamba")
            compress_start = datetime.now()
            compressed_contexts = self._compress_contexts(refactor_plans, context_limit)
            compress_duration = (datetime.now() - compress_start).total_seconds() * 1000
            
            # Log Phase 3 model usage (Compressor)
            if not self.use_mock and self.context_encoder:
                estimated_tokens = context_limit * len(refactor_plans)
                provenance_logger.log_model_usage(
                    phase="compressor",
                    model_name="jamba-1.5-mini",
                    purpose="compressing context to fit within token limit",
                    tokens_used=estimated_tokens,
                    duration_ms=compress_duration
                )
            
            # Step 3: Generate patches (Phase 4)
            logger.info("Phase 4: Generating code with diffusion")
            gen_start = datetime.now()
            patches = self._generate_patches(refactor_plans)
            gen_duration = (datetime.now() - gen_start).total_seconds() * 1000
            
            # Log Phase 4 model usage (Generator)
            for patch in patches:
                if patch.diffusion_sample:
                    provenance_logger.log_model_usage(
                        phase="generator",
                        model_name=f"diffusion-{self.diffusion_config.backbone.value}",
                        purpose="generating refactored code",
                        tokens_used=0,  # Diffusion doesn't use tokens in traditional sense
                        duration_ms=patch.metadata.get("generation_time_ms", 0),
                        num_steps=patch.metadata.get("num_steps", 0),
                        cfg_scale=patch.metadata.get("cfg_scale", 0),
                        retry_count=patch.metadata.get("retry_count", 0)
                    )
                    
                    # Log safety check for this patch
                    provenance_logger.log_safety_check(
                        check_type="syntax_validation",
                        passed=patch.is_valid_syntax,
                        details=(
                            "Syntax validation passed" if patch.is_valid_syntax
                            else f"Syntax errors: {'; '.join(patch.validation_errors[:3])}"
                        )
                    )
            
            # Create result
            duration = (datetime.now() - start_time).total_seconds()
            result = GenerationResult(
                patches=patches,
                refactor_plans=refactor_plans,
                compressed_contexts=compressed_contexts,
                success=True,
                metadata={
                    "duration_seconds": duration,
                    "num_plans": len(refactor_plans),
                    "num_patches": len(patches),
                    "num_applicable": len([p for p in patches if p.can_apply()]),
                    "config": config,
                    "timestamp": start_time.isoformat(),
                }
            )
            
            logger.info(
                f"Generation complete: {len(patches)} patches in {duration:.2f}s "
                f"({result.metadata['num_applicable']} applicable)"
            )
            
            # Finalize provenance logging
            provenance_logger.finalize(success=True)
            
            # Save provenance metadata
            artifacts_dir = Path("./artifacts")
            artifacts_dir.mkdir(exist_ok=True)
            provenance_path = artifacts_dir / f"artifact_metadata_{provenance_logger.metadata.run_id}.json"
            provenance_logger.save(provenance_path)
            logger.info(f"Saved provenance metadata to {provenance_path}")
            
            # Add provenance path to result metadata
            result.metadata["provenance_file"] = str(provenance_path)
            
            return result
        
        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            duration = (datetime.now() - start_time).total_seconds()
            
            # Log error to provenance
            provenance_logger.log_error(str(e))
            provenance_logger.finalize(success=False)
            
            # Save provenance even on failure (for debugging)
            try:
                artifacts_dir = Path("./artifacts")
                artifacts_dir.mkdir(exist_ok=True)
                provenance_path = artifacts_dir / f"artifact_metadata_{provenance_logger.metadata.run_id}_failed.json"
                provenance_logger.save(provenance_path)
                logger.info(f"Saved failure provenance metadata to {provenance_path}")
            except Exception as save_error:
                logger.error(f"Failed to save provenance metadata: {save_error}")
            
            return GenerationResult(
                patches=[],
                refactor_plans=[],
                compressed_contexts=[],
                success=False,
                errors=[str(e)],
                metadata={
                    "duration_seconds": duration,
                    "timestamp": start_time.isoformat(),
                }
            )
    
    def _create_refactor_plans(
        self,
        request: GenerationRequest
    ) -> List[RefactorPlan]:
        """
        Create refactor plans using Phase 2 Reasoner.
        
        Steps:
        1. Retrieve relevant code from graph
        2. Analyze dependencies and impact
        3. Identify refactoring opportunities
        4. Create prioritized refactor plans
        """
        plans = []
        
        # If specific files provided, analyze those
        if request.target_files:
            for file_path in request.target_files:
                # Retrieve file from graph
                file_nodes = self.retriever.get_nodes_by_property(
                    "File",
                    "path",
                    str(file_path)
                )
                
                if not file_nodes:
                    logger.warning(f"File not found in graph: {file_path}")
                    continue
                
                file_node = file_nodes[0]
                
                # Get functions in file
                functions = self.retriever.get_related_nodes(
                    file_node["id"],
                    relationship_type="CONTAINS",
                    target_label="Function"
                )
                
                # If specific functions requested, filter
                if request.target_functions:
                    functions = [
                        f for f in functions
                        if f.get("name") in request.target_functions
                    ]
                
                # Create plans for each function
                for func in functions:
                    # Analyze dependencies
                    dependencies = self.dependency_analyzer.get_dependencies(
                        func["id"]
                    )
                    
                    # Calculate simple impact based on dependencies
                    impact_score = min(1.0, len(dependencies) / 20.0)  # More deps = higher impact
                    impact = {
                        "impact_score": impact_score,
                        "num_dependencies": len(dependencies)
                    }
                    
                    # Determine language
                    language = self._determine_language(file_path)
                    
                    # Create refactor plan
                    plan = RefactorPlan(
                        file_path=file_path,
                        edit_targets=[func.get("name", "unknown")],
                        intent=request.issue_description,
                        condition=self._create_condition(
                            request.issue_description,
                            func,
                            dependencies,
                            impact
                        ),
                        context={
                            "dependencies": dependencies[:10],  # Limit size
                            "impact_score": impact.get("impact_score", 0.5),
                            "file_node_id": file_node["id"],
                            "func_node_id": func["id"],
                        },
                        language=language,
                        priority=self._calculate_priority(func, impact, request.priority)
                    )
                    
                    plans.append(plan)
        
        else:
            # No specific files - search graph for relevant code
            # This would use semantic search or keyword matching
            logger.info("No target files specified - searching graph")
            
            # TODO: Implement semantic search in graph
            # For now, return empty list
            logger.warning("Graph-wide search not yet implemented")
        
        return plans
    
    def _compress_contexts(
        self,
        plans: List[RefactorPlan],
        context_limit: int
    ) -> List[Dict[str, Any]]:
        """
        Compress context using Phase 3 Context Encoder (Jamba).
        
        For each refactor plan:
        1. Gather relevant context from graph
        2. Compress with Jamba to fit within token limit
        3. Add compressed context to plan
        """
        if self.use_mock or not self.context_encoder:
            logger.info("Skipping context compression (mock mode)")
            return []
        
        compressed_contexts = []
        
        for plan in plans:
            try:
                # Gather context
                context_text = self._gather_context(plan)
                
                # Compress with Context Encoder
                compressed = self.context_encoder.compress(
                    text=context_text,
                    max_tokens=context_limit
                )
                
                compressed_contexts.append(compressed)
                
                # Add to plan context
                plan.context["compressed_context"] = compressed
                if hasattr(compressed, "compression_ratio"):
                    plan.context["compression_ratio"] = compressed.compression_ratio
                
            except Exception as e:
                logger.error(f"Context compression failed for {plan.file_path}: {e}")
        
        return compressed_contexts
    
    def _generate_patches(
        self,
        plans: List[RefactorPlan]
    ) -> List[GeneratedPatch]:
        """
        Generate patches using Phase 4 Builder.
        
        Uses batch generation for efficiency.
        """
        logger.info(f"Generating patches for {len(plans)} plans")
        
        try:
            patches = self.builder.generate_batch(
                plans=plans,
                use_fallback=True,
                max_retries=3
            )
            
            return patches
        
        except Exception as e:
            logger.error(f"Patch generation failed: {e}", exc_info=True)
            return []
    
    def _gather_context(self, plan: RefactorPlan) -> str:
        """
        Gather relevant context from graph for a refactor plan.
        
        Includes:
        - Target function code
        - Dependencies
        - Callers
        - Related functions
        - Documentation
        """
        context_parts = []
        
        # Add issue description
        context_parts.append(f"# Task\n{plan.intent}\n")
        
        # Add target function
        if "func_node_id" in plan.context:
            func_node = self.retriever.get_node(plan.context["func_node_id"])
            if func_node and "code" in func_node:
                context_parts.append(f"# Current Implementation\n```python\n{func_node['code']}\n```\n")
        
        # Add dependencies
        if "dependencies" in plan.context:
            deps = plan.context["dependencies"]
            if deps:
                context_parts.append("# Dependencies\n")
                for dep in deps[:5]:  # Limit
                    context_parts.append(f"- {dep.get('name', 'unknown')}\n")
        
        return "\n".join(context_parts)
    
    def _create_condition(
        self,
        issue_description: str,
        func_node: Dict[str, Any],
        dependencies: List[Dict[str, Any]],
        impact: Dict[str, Any]
    ) -> str:
        """
        Create detailed condition/prompt for diffusion model.
        
        This is critical - the quality of the condition directly
        affects the quality of generated code.
        """
        parts = []
        
        # Main task
        parts.append(f"Task: {issue_description}")
        
        # Function context
        func_name = func_node.get("name", "unknown")
        parts.append(f"\nRefactor the function '{func_name}'.")
        
        # Constraints
        parts.append("\nConstraints:")
        parts.append("- Preserve the function signature")
        parts.append("- Maintain backward compatibility")
        parts.append("- Add appropriate error handling")
        
        # Dependencies context
        if dependencies:
            dep_names = [d.get("name", "unknown") for d in dependencies[:3]]
            parts.append(f"- Uses: {', '.join(dep_names)}")
        
        # Impact context
        impact_score = impact.get("impact_score", 0.5)
        if impact_score > 0.7:
            parts.append("- High impact change - be conservative")
        
        return "\n".join(parts)
    
    def _determine_language(self, file_path: Path) -> str:
        """Determine programming language from file extension."""
        ext = file_path.suffix.lower()
        
        mapping = {
            ".py": "python",
            ".ts": "typescript",
            ".js": "javascript",
            ".tsx": "typescript",
            ".jsx": "javascript",
        }
        
        return mapping.get(ext, "python")
    
    def _calculate_priority(
        self,
        func_node: Dict[str, Any],
        impact: Dict[str, Any],
        base_priority: int
    ) -> int:
        """
        Calculate priority for refactor plan.
        
        Factors:
        - Base priority from request
        - Impact score (higher impact = higher priority)
        - Complexity (simpler = higher priority)
        """
        priority = base_priority
        
        # Boost for high impact
        impact_score = impact.get("impact_score", 0.5)
        if impact_score > 0.7:
            priority += 2
        elif impact_score > 0.5:
            priority += 1
        
        # Reduce for high complexity
        complexity = func_node.get("complexity", 0)
        if complexity > 20:
            priority -= 2
        elif complexity > 10:
            priority -= 1
        
        return max(1, min(10, priority))
    
    def _update_config(self, config_name: str):
        """Update diffusion config."""
        config_map = {
            "fast": FAST_CONFIG,
            "balanced": BALANCED_CONFIG,
            "quality": QUALITY_CONFIG,
            "mock": MOCK_CONFIG,
        }
        
        if config_name.lower() in config_map:
            self.diffusion_config = config_map[config_name.lower()]
            self.builder = Builder(config=self.diffusion_config)
            logger.info(f"Updated config to: {config_name}")
    
    def apply_patch(
        self,
        patch: GeneratedPatch,
        backup: bool = True,
        dry_run: bool = False,
        provenance_logger: Optional[ProvenanceLogger] = None
    ) -> bool:
        """
        Apply a generated patch to the filesystem.
        
        Args:
            patch: Patch to apply
            backup: Create backup before applying
            dry_run: Don't actually modify files
            provenance_logger: Optional provenance logger to track modifications
        
        Returns:
            True if successful
        """
        if not patch.can_apply():
            logger.error(f"Cannot apply patch - invalid syntax or errors")
            return False
        
        if patch.risk_score() > 0.7:
            logger.warning(f"High risk patch (score: {patch.risk_score():.2f})")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would apply patch to {patch.file_path}")
            logger.info(f"Diff:\n{patch.unified_diff}")
            return True
        
        try:
            # Create backup
            backup_path = None
            if backup:
                backup_path = Path(str(patch.file_path) + ".backup")
                backup_path.write_text(patch.original_code)
                logger.info(f"Created backup: {backup_path}")
            
            # Write new code
            patch.file_path.write_text(patch.generated_code, encoding="utf-8")
            logger.info(f"Applied patch to {patch.file_path}")
            
            # Log to provenance if logger provided
            if provenance_logger:
                # Count lines added/removed from unified diff
                lines_added = len([l for l in patch.unified_diff.split('\n') if l.startswith('+')])
                lines_removed = len([l for l in patch.unified_diff.split('\n') if l.startswith('-')])
                
                provenance_logger.log_file_modification(
                    file_path=str(patch.file_path),
                    original_content=patch.original_code,
                    modified_content=patch.generated_code,
                    lines_added=lines_added,
                    lines_removed=lines_removed,
                    backup_path=str(backup_path) if backup_path else None
                )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to apply patch: {e}", exc_info=True)
            return False
    
    def close(self):
        """Close database connections."""
        self.graph_db.close()
        logger.info("Ouroboros pipeline closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Example with mock mode (no real API calls or database)
    print("=" * 80)
    print("Ouroboros Code Generator - Mock Example")
    print("=" * 80)
    
    # This would normally connect to a real Neo4j database
    # For this example, we'll show the API
    
    try:
        with OuroborosCodeGenerator(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            use_mock=True  # Mock mode for testing
        ) as generator:
            
            # Generate patches
            result = generator.generate(
                issue_description="Add caching to improve performance",
                target_files=["src/services/user_service.py"],
                target_functions=["get_user_by_id"],
                config="mock"
            )
            
            print(f"\nGeneration Result:")
            print(f"  Success: {result.success}")
            print(f"  Total patches: {len(result.patches)}")
            print(f"  Applicable patches: {len(result.get_applicable_patches())}")
            print(f"  High-risk patches: {len(result.get_high_risk_patches())}")
            
            # Show applicable patches
            for i, patch in enumerate(result.get_applicable_patches(), 1):
                print(f"\nPatch {i}:")
                print(f"  File: {patch.file_path}")
                print(f"  Risk: {patch.risk_score():.2f}")
                print(f"  Valid: {patch.is_valid_syntax}")
            
            # Apply patches (dry run)
            for patch in result.get_applicable_patches(max_risk=0.3):
                generator.apply_patch(patch, dry_run=True)
    
    except Exception as e:
        print(f"Error: {e}")
