"""
Context Integrity Validator
============================

Validates compressed context to prevent hallucination and ensure quality.
"""

from dataclasses import dataclass
from typing import List, Set

from .config import ContextEncoderConfig


@dataclass
class ValidationResult:
    """Result of context integrity validation."""
    
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    score: float  # 0.0 to 1.0


class ContextIntegrityValidator:
    """
    Validates compressed context to ensure:
    1. No hallucinations (references actual files)
    2. Minimum quality standards
    3. Contains required structural information
    """
    
    def __init__(self, config: ContextEncoderConfig):
        self.config = config
    
    def validate(
        self,
        compressed_context: "CompressedContext",
        original_context: str,
    ) -> ValidationResult:
        """
        Validate the compressed context against the original.
        
        Args:
            compressed_context: The compressed context from Jamba
            original_context: The original GraphRAG subgraph
        
        Returns:
            ValidationResult with pass/fail and error details
        """
        errors = []
        warnings = []
        score = 1.0
        
        # Check 1: Minimum length
        if len(compressed_context.summary) < self.config.min_summary_length:
            errors.append(
                f"Summary too short: {len(compressed_context.summary)} chars "
                f"(minimum: {self.config.min_summary_length})"
            )
            score -= 0.3
        
        # Check 2: Not empty
        if not compressed_context.summary.strip():
            errors.append("Summary is empty or whitespace only")
            score -= 0.5
        
        # Check 3: File references validation
        if self.config.require_file_references:
            file_ref_errors = self._validate_file_references(
                compressed_context.summary,
                compressed_context.file_references,
                original_context,
            )
            errors.extend(file_ref_errors)
            if file_ref_errors:
                score -= 0.2
        
        # Check 4: Hallucination detection
        hallucination_score = self._detect_hallucinations(
            compressed_context.summary, original_context
        )
        if hallucination_score > self.config.max_hallucination_score:
            warnings.append(
                f"High hallucination score: {hallucination_score:.2f} "
                f"(threshold: {self.config.max_hallucination_score})"
            )
            # Reduce score proportionally but don't fail completely
            score -= min(hallucination_score * 0.3, 0.3)
        
        # Check 5: Structural completeness
        structure_warnings = self._check_structural_completeness(
            compressed_context.summary
        )
        warnings.extend(structure_warnings)
        
        is_valid = len(errors) == 0 and score >= 0.5
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            score=max(0.0, min(1.0, score)),
        )
    
    def _validate_file_references(
        self,
        summary: str,
        target_files: List[str],
        original_context: str,
    ) -> List[str]:
        """Ensure summary references actual files from the context."""
        errors = []
        
        # Extract file names mentioned in summary
        summary_lower = summary.lower()
        
        for file in target_files:
            file_name = file.split("/")[-1].lower()  # Get basename
            
            # Check if file is mentioned
            if file_name not in summary_lower and file.lower() not in summary_lower:
                errors.append(f"Target file not referenced in summary: {file}")
        
        return errors
    
    def _detect_hallucinations(
        self, summary: str, original_context: str
    ) -> float:
        """
        Detect potential hallucinations in the summary.
        
        Returns a score from 0.0 (no hallucination) to 1.0 (high hallucination).
        """
        # Simple keyword-based detection (can be improved with embeddings)
        
        # Extract potential identifiers from summary
        summary_words = set(summary.lower().split())
        context_words = set(original_context.lower().split())
        
        # Find words in summary but not in context (potential hallucinations)
        # Filter out common words
        common_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were",
            "file", "function", "class", "import", "export", "const", "let", "var",
            "this", "that", "these", "those", "it", "they", "we", "you",
        }
        
        summary_unique = summary_words - context_words - common_words
        
        # Calculate hallucination ratio
        if len(summary_words) == 0:
            return 0.0
        
        hallucination_ratio = len(summary_unique) / len(summary_words)
        
        # Score between 0-1 (capped at reasonable threshold)
        return min(hallucination_ratio * 2, 1.0)
    
    def _check_structural_completeness(self, summary: str) -> List[str]:
        """Check if summary contains expected structural elements."""
        warnings = []
        summary_lower = summary.lower()
        
        expected_keywords = {
            "function": ["function", "def", "method"],
            "class": ["class", "interface", "type"],
            "import": ["import", "require", "from"],
        }
        
        for category, keywords in expected_keywords.items():
            if not any(kw in summary_lower for kw in keywords):
                warnings.append(
                    f"Summary may be incomplete: no {category} definitions found"
                )
        
        return warnings
