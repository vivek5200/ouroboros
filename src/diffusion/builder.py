"""
Phase 4: The Builder - High-level orchestrator for code generation.

This module provides the Builder class that orchestrates the entire code generation
pipeline by consuming RefactorPlans from the Reasoner and producing validated patches.

Architecture:
    RefactorPlan (Phase 2) → CompressedContext (Phase 3) → Builder (Phase 4) → Patch

The Builder:
1. Receives RefactorPlan with strategic edit locations
2. Uses ASTMasker to mask code at edit locations
3. Runs discrete diffusion to generate new code
4. Validates syntax with Tree-Sitter
5. Falls back to autoregressive if needed
6. Produces unified diff patches with provenance
7. Tracks generation metadata for rollback

Created: 2025-01-09 (Phase 4 implementation)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import difflib
import time
from datetime import datetime
import logging

from .config import DiffusionConfig, BALANCED_CONFIG
from .diffusion_model import DiscreteDiffusionModel, DiffusionSample
from .masking import ASTMasker, MaskedSpan
from ..utils.syntax_validator import SyntaxValidator, ValidationResult
from ..utils.semantic_analyzer import SemanticAnalyzer, SemanticResult
from ..utils.provenance_logger import ProvenanceLogger

logger = logging.getLogger(__name__)


@dataclass
class RefactorPlan:
    """
    Strategic refactor plan from Phase 2 Reasoner.
    
    This is the output of the Reasoner that tells the Builder:
    - What files to edit
    - What functions/classes to modify
    - What the high-level intent is
    - What the condition/prompt should be
    
    Attributes:
        file_path: Path to file to edit
        edit_targets: List of function/class names to refactor
        intent: High-level description of the refactor
        condition: Detailed prompt for diffusion model
        context: Additional context from compressed graph
        language: Programming language (python, typescript, etc.)
        priority: Priority level (higher = more important)
    """
    file_path: Path
    edit_targets: List[str]
    intent: str
    condition: str
    context: Dict[str, Any] = field(default_factory=dict)
    language: str = "python"
    priority: int = 1


@dataclass
class GeneratedPatch:
    """
    Generated code patch with provenance and validation metadata.
    
    This is the output of the Builder that can be applied to the codebase.
    Contains everything needed for:
    - Applying the patch
    - Rolling back if needed
    - Understanding how it was generated
    - Validating before commit
    
    Attributes:
        file_path: Path to file to patch
        original_code: Original code before edit
        generated_code: New code after edit
        unified_diff: Standard unified diff format
        masked_spans: Spans that were masked and regenerated
        diffusion_sample: Full diffusion generation metadata
        refactor_plan: Original plan that generated this patch
        is_valid_syntax: Whether generated code parses
        validation_errors: List of validation errors (if any)
        generation_timestamp: When patch was generated
        metadata: Additional metadata
    """
    file_path: Path
    original_code: str
    generated_code: str
    unified_diff: str
    masked_spans: List[MaskedSpan]
    diffusion_sample: DiffusionSample
    refactor_plan: RefactorPlan
    is_valid_syntax: bool
    validation_errors: List[str]
    generation_timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def can_apply(self) -> bool:
        """Check if patch is safe to apply."""
        return self.is_valid_syntax and len(self.validation_errors) == 0
    
    def risk_score(self) -> float:
        """
        Compute risk score for applying this patch.
        
        Returns:
            Risk score from 0.0 (safe) to 1.0 (risky)
        """
        score = 0.0
        
        # Invalid syntax = high risk
        if not self.is_valid_syntax:
            score += 0.5
        
        # Validation errors = medium risk
        if self.validation_errors:
            score += 0.3
        
        # Large diffs = higher risk
        lines_changed = len([l for l in self.unified_diff.split('\n') 
                            if l.startswith('+') or l.startswith('-')])
        if lines_changed > 100:
            score += 0.2
        elif lines_changed > 50:
            score += 0.1
        
        return min(1.0, score)


class Builder:
    """
    Phase 4: The Builder - Orchestrates code generation pipeline.
    
    The Builder is the high-level interface for generating code patches.
    It coordinates:
    - AST masking (which code to regenerate)
    - Discrete diffusion (how to generate new code)
    - Validation (is the new code valid?)
    - Fallback (retry with autoregressive if needed)
    - Provenance (track how code was generated)
    
    Usage:
        ```python
        from src.diffusion.builder import Builder, RefactorPlan
        from src.diffusion.config import BALANCED_CONFIG
        from pathlib import Path
        
        # Create builder
        builder = Builder(config=BALANCED_CONFIG)
        
        # Create refactor plan
        plan = RefactorPlan(
            file_path=Path("src/utils.py"),
            edit_targets=["calculate_total"],
            intent="Optimize performance",
            condition="Refactor to use vectorized operations with numpy",
            language="python"
        )
        
        # Generate patch
        patch = builder.generate_patch(plan)
        
        # Check if safe to apply
        if patch.can_apply():
            print(patch.unified_diff)
            # Apply patch...
        else:
            print(f"Patch has errors: {patch.validation_errors}")
        ```
    
    Attributes:
        config: Diffusion model configuration
        model: Discrete diffusion model
        masker: AST masker for identifying edit spans
    """
    
    def __init__(
        self,
        config: DiffusionConfig = BALANCED_CONFIG,
        model: Optional[DiscreteDiffusionModel] = None,
        masker: Optional[ASTMasker] = None,
        enable_safety_gate: bool = True,
        max_retry_attempts: int = 3
    ):
        """
        Initialize Builder.
        
        Args:
            config: Diffusion configuration (defaults to BALANCED_CONFIG)
            model: Pre-initialized diffusion model (optional)
            masker: Pre-initialized AST masker (optional)
            enable_safety_gate: Enable syntax validation before applying changes
            max_retry_attempts: Maximum retry attempts for self-healing
        """
        self.config = config
        self.model = model or DiscreteDiffusionModel(config)
        self.masker = masker or ASTMasker()
        self.enable_safety_gate = enable_safety_gate
        self.max_retry_attempts = max_retry_attempts
        
        # Initialize syntax validator for safety gate
        if enable_safety_gate:
            self.validator = SyntaxValidator()
            self.semantic_analyzer = SemanticAnalyzer()
        else:
            self.validator = None
            self.semantic_analyzer = None
    
    def generate_patch(
        self,
        plan: RefactorPlan,
        use_fallback: bool = True,
        max_retries: int = 3
    ) -> GeneratedPatch:
        """
        Generate code patch from refactor plan.
        
        This is the main entry point for code generation. It:
        1. Reads original code from file
        2. Masks target functions/classes
        3. Runs diffusion to generate new code
        4. Validates syntax
        5. Falls back to autoregressive if needed
        6. Creates unified diff
        7. Returns patch with full provenance
        
        Args:
            plan: Refactor plan from Reasoner
            use_fallback: Whether to use autoregressive fallback on failure
            max_retries: Maximum number of retries
        
        Returns:
            GeneratedPatch with all metadata
        
        Raises:
            FileNotFoundError: If plan.file_path doesn't exist
            ValueError: If plan is invalid
        """
        start_time = time.time()
        
        # Validate plan
        if not plan.file_path.exists():
            raise FileNotFoundError(f"File not found: {plan.file_path}")
        
        if not plan.edit_targets:
            raise ValueError("RefactorPlan must have at least one edit target")
        
        # Read original code
        original_code = plan.file_path.read_text(encoding="utf-8")
        
        # Mask target functions/classes
        # We use a special method to mask specific function names
        masked_code, masked_spans = self._mask_target_functions(
            code=original_code,
            target_names=plan.edit_targets,
            language=plan.language
        )
        
        if not masked_spans:
            raise ValueError(
                f"Could not find any of {plan.edit_targets} in {plan.file_path}"
            )
        
        # Generate new code with safety gate and retry loop
        retry_count = 0
        diffusion_sample = None
        last_validation_result = None
        
        while retry_count <= max_retries:
            # Generate code
            if use_fallback:
                diffusion_sample = self.model.generate_with_fallback(
                    masked_code=masked_code,
                    masked_spans=masked_spans,
                    condition=plan.condition,
                    language=plan.language
                )
            else:
                diffusion_sample = self.model.generate(
                    masked_code=masked_code,
                    masked_spans=masked_spans,
                    condition=plan.condition,
                    language=plan.language
                )
            
            # Safety Gate: Validate syntax AND semantics before accepting
            if self.enable_safety_gate and self.validator:
                # Step 1: Syntax validation
                validation_result = self.validator.validate(
                    diffusion_sample.generated_code,
                    language=plan.language
                )
                
                last_validation_result = validation_result
                
                if not validation_result.is_valid:
                    # Invalid syntax - retry
                    retry_count += 1
                    logger.warning(
                        f"✗ Syntax validation failed on attempt {retry_count}. "
                        f"Errors: {validation_result.error_summary}"
                    )
                    
                    if retry_count <= max_retries:
                        logger.info(f"Self-healing: Retrying with enhanced condition...")
                        enhanced_condition = (
                            f"{plan.condition}\n\n"
                            f"IMPORTANT: Previous attempt had syntax errors. "
                            f"Fix these issues: {validation_result.error_summary}"
                        )
                        plan.condition = enhanced_condition
                        continue
                    else:
                        logger.error(
                            f"✗ Max retries ({max_retries}) exceeded. "
                            f"Final error: {validation_result.error_summary}"
                        )
                        break
                
                # Step 2: Semantic analysis (if syntax is valid)
                semantic_result = None
                if self.semantic_analyzer:
                    semantic_result = self.semantic_analyzer.analyze(
                        diffusion_sample.generated_code,
                        language=plan.language
                    )
                    
                    if not semantic_result.is_valid:
                        # Semantic errors found - retry
                        retry_count += 1
                        logger.warning(
                            f"✗ Semantic analysis failed on attempt {retry_count}. "
                            f"Errors: {semantic_result.error_summary}"
                        )
                        
                        if retry_count <= max_retries:
                            logger.info(f"Self-healing: Retrying with semantic feedback...")
                            enhanced_condition = (
                                f"{plan.condition}\n\n"
                                f"IMPORTANT: Previous attempt had semantic errors. "
                                f"Fix these issues: {semantic_result.error_summary}"
                            )
                            plan.condition = enhanced_condition
                            continue
                        else:
                            logger.error(
                                f"✗ Max retries ({max_retries}) exceeded. "
                                f"Final semantic error: {semantic_result.error_summary}"
                            )
                            break
                
                # Both syntax and semantics valid - accept
                logger.info(f"✓ Syntax and semantic validation passed on attempt {retry_count + 1}")
                if semantic_result:
                    logger.info(f"  Checker: {semantic_result.checker_used}, Warnings: {len(semantic_result.warnings)}")
                break
            else:
                # Safety gate disabled - accept immediately
                break
        
        # Update diffusion sample with validation info
        if last_validation_result and self.enable_safety_gate:
            diffusion_sample.is_valid_syntax = last_validation_result.is_valid
            diffusion_sample.validation_errors = [
                f"Line {e.line}: {e.message}" for e in last_validation_result.errors
            ]
            diffusion_sample.metadata["validation_result"] = {
                "parse_time_ms": last_validation_result.parse_time_ms,
                "has_error_nodes": last_validation_result.has_error_nodes,
                "num_errors": len(last_validation_result.errors)
            }
        
        diffusion_sample.metadata["retry_count"] = retry_count
        
        # Create unified diff
        unified_diff = self._create_unified_diff(
            original_code,
            diffusion_sample.generated_code,
            str(plan.file_path)
        )
        
        # Create patch
        generation_time = (time.time() - start_time) * 1000  # ms
        
        patch = GeneratedPatch(
            file_path=plan.file_path,
            original_code=original_code,
            generated_code=diffusion_sample.generated_code,
            unified_diff=unified_diff,
            masked_spans=masked_spans,
            diffusion_sample=diffusion_sample,
            refactor_plan=plan,
            is_valid_syntax=diffusion_sample.is_valid_syntax,
            validation_errors=diffusion_sample.validation_errors,
            generation_timestamp=datetime.now().isoformat(),
            metadata={
                "generation_time_ms": generation_time,
                "num_masked_spans": len(masked_spans),
                "num_retries": diffusion_sample.metadata.get("num_retries", 0),
                "used_fallback": diffusion_sample.metadata.get("used_fallback", False),
                "backbone": self.config.backbone.value,
                "num_steps": self.config.num_sampling_steps,
                "cfg_scale": self.config.cfg_guidance_scale,
            }
        )
        
        return patch
    
    def generate_batch(
        self,
        plans: List[RefactorPlan],
        use_fallback: bool = True,
        max_retries: int = 3
    ) -> List[GeneratedPatch]:
        """
        Generate patches for multiple refactor plans.
        
        Processes plans in priority order (higher priority first).
        
        Args:
            plans: List of refactor plans
            use_fallback: Whether to use autoregressive fallback
            max_retries: Maximum retries per plan
        
        Returns:
            List of generated patches (same order as input)
        """
        # Sort by priority (descending)
        sorted_plans = sorted(plans, key=lambda p: p.priority, reverse=True)
        
        patches = []
        for plan in sorted_plans:
            try:
                patch = self.generate_patch(
                    plan=plan,
                    use_fallback=use_fallback,
                    max_retries=max_retries
                )
                patches.append(patch)
            except Exception as e:
                # Create error patch
                patches.append(self._create_error_patch(plan, str(e)))
        
        return patches
    
    def _mask_target_functions(
        self,
        code: str,
        target_names: List[str],
        language: str
    ) -> tuple[str, List[MaskedSpan]]:
        """
        Mask specific functions/classes by name.
        
        This is a wrapper around ASTMasker that finds and masks specific
        named functions or classes. It uses Tree-Sitter to find the functions
        and then masks their entire definition.
        
        Args:
            code: Source code
            target_names: List of function/class names to mask
            language: Programming language
        
        Returns:
            Tuple of (masked_code, masked_spans)
        
        Raises:
            ValueError: If no target names found
        """
        # Create language-specific masker if needed
        if self.masker.language != language:
            masker = ASTMasker(language=language)
        else:
            masker = self.masker
        
        # Parse code
        tree = masker.parser.parse(bytes(code, "utf8"))
        root = tree.root_node
        
        # Find target nodes by name
        target_nodes = []
        target_node_types = {
            "python": ["function_definition", "class_definition"],
            "typescript": ["function_declaration", "function_signature", "class_declaration", "method_definition"],
            "javascript": ["function_declaration", "class_declaration", "method_definition"],
        }
        
        node_types = target_node_types.get(language, ["function_definition", "class_definition"])
        
        def find_named_nodes(node):
            """Recursively find nodes with matching names."""
            # Check if this node is a target type
            if node.type in node_types:
                # Extract the name - look for identifier child
                name_node = None
                for child in node.children:
                    if child.type in ("identifier", "property_identifier"):
                        name_node = child
                        break
                
                if name_node:
                    node_name = code[name_node.start_byte:name_node.end_byte]
                    if node_name in target_names:
                        target_nodes.append(node)
                        return  # Don't recurse into matched nodes
            
            # Recurse on children
            for child in node.children:
                find_named_nodes(child)
        
        find_named_nodes(root)
        
        if not target_nodes:
            return code, []
        
        # Sort by position (reverse for safe replacement)
        target_nodes.sort(key=lambda n: n.start_byte, reverse=True)
        
        # Create masked spans
        masked_spans = []
        masked_code = code
        
        for node in target_nodes:
            span = masker._create_masked_span(node, code)
            masked_spans.append(span)
            
            # Replace with [MASK]
            before = masked_code[:node.start_byte]
            after = masked_code[node.end_byte:]
            masked_code = before + "[MASK]" + after
        
        return masked_code, masked_spans
    
    def _create_unified_diff(
        self,
        original: str,
        generated: str,
        filename: str
    ) -> str:
        """
        Create unified diff between original and generated code.
        
        Args:
            original: Original code
            generated: Generated code
            filename: Filename for diff header
        
        Returns:
            Unified diff string
        """
        original_lines = original.splitlines(keepends=True)
        generated_lines = generated.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            generated_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )
        
        return "".join(diff)
    
    def _create_error_patch(
        self,
        plan: RefactorPlan,
        error: str
    ) -> GeneratedPatch:
        """
        Create error patch when generation fails.
        
        Args:
            plan: Original refactor plan
            error: Error message
        
        Returns:
            GeneratedPatch with error metadata
        """
        # Create dummy diffusion sample
        from .diffusion_model import DiffusionSample
        
        diffusion_sample = DiffusionSample(
            generated_code="",
            masked_spans=[],
            num_steps=0,
            cfg_scale=0.0,
            is_valid_syntax=False,
            validation_errors=[error],
            generation_time_ms=0.0,
            metadata={"error": True}
        )
        
        return GeneratedPatch(
            file_path=plan.file_path,
            original_code="",
            generated_code="",
            unified_diff="",
            masked_spans=[],
            diffusion_sample=diffusion_sample,
            refactor_plan=plan,
            is_valid_syntax=False,
            validation_errors=[error],
            generation_timestamp=datetime.now().isoformat(),
            metadata={"error": True}
        )


# Example usage
if __name__ == "__main__":
    from .config import MOCK_CONFIG
    from pathlib import Path
    
    # Create mock builder for testing
    builder = Builder(config=MOCK_CONFIG)
    
    # Example: Refactor a function
    example_code = '''
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price']
    return total
'''
    
    # Save to temp file
    temp_file = Path("temp_example.py")
    temp_file.write_text(example_code)
    
    try:
        # Create refactor plan
        plan = RefactorPlan(
            file_path=temp_file,
            edit_targets=["calculate_total"],
            intent="Optimize performance",
            condition="Refactor to use sum() and generator expression",
            language="python"
        )
        
        # Generate patch
        patch = builder.generate_patch(plan)
        
        print("=" * 80)
        print("GENERATED PATCH")
        print("=" * 80)
        print(f"File: {patch.file_path}")
        print(f"Valid syntax: {patch.is_valid_syntax}")
        print(f"Risk score: {patch.risk_score():.2f}")
        print(f"Can apply: {patch.can_apply()}")
        print(f"Generation time: {patch.metadata['generation_time_ms']:.2f}ms")
        print("\nUnified diff:")
        print(patch.unified_diff)
        
    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()
