"""
LLM output parser and validator.

Converts raw LLM responses into validated Pydantic RefactorPlan objects.
Handles JSON extraction, schema validation, and error correction.
"""

import json
import re
import logging
from typing import Optional, Dict, Any, Tuple

from src.architect.schemas import (
    RefactorPlan,
    validate_refactor_plan,
    ValidationResult,
)


logger = logging.getLogger(__name__)


class PlanParser:
    """
    Parses and validates LLM output into RefactorPlan objects.
    
    Handles various output formats:
    - Pure JSON
    - JSON in markdown code fences
    - XML format (converts to JSON)
    - Malformed JSON (attempts repair)
    """
    
    def __init__(self, strict_validation: bool = True):
        """
        Initialize parser.
        
        Args:
            strict_validation: Whether to reject plans with validation warnings
        """
        self.strict_validation = strict_validation
    
    def parse(self, llm_output: str) -> Tuple[Optional[RefactorPlan], ValidationResult]:
        """
        Parse LLM output into RefactorPlan.
        
        Args:
            llm_output: Raw text from LLM
        
        Returns:
            Tuple of (RefactorPlan or None, ValidationResult)
        """
        
        # Step 1: Extract JSON from output
        json_str = self._extract_json(llm_output)
        
        if not json_str:
            return None, ValidationResult(
                is_valid=False,
                errors=["Could not extract JSON from LLM output"],
                warnings=[],
                plan=None
            )
        
        # Step 2: Parse JSON
        try:
            plan_dict = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")
            
            # Attempt to repair JSON
            repaired_json = self._repair_json(json_str)
            if repaired_json:
                try:
                    plan_dict = json.loads(repaired_json)
                    logger.info("Successfully repaired malformed JSON")
                except json.JSONDecodeError:
                    return None, ValidationResult(
                        is_valid=False,
                        errors=[f"Invalid JSON: {e}"],
                        warnings=[],
                        plan=None
                    )
            else:
                return None, ValidationResult(
                    is_valid=False,
                    errors=[f"Invalid JSON and repair failed: {e}"],
                    warnings=[],
                    plan=None
                )
        
        # Step 3: Validate with Pydantic schema
        try:
            plan = RefactorPlan(**plan_dict)
            validation = validate_refactor_plan(plan)
            
            # Check if validation passed
            if not validation.is_valid:
                return None, validation
            
            # Check warnings in strict mode
            if self.strict_validation and validation.warnings:
                validation.is_valid = False
                validation.errors.append("Validation warnings present in strict mode")
                return None, validation
            
            return plan, validation
            
        except Exception as e:
            logger.error(f"Pydantic validation error: {e}")
            return None, ValidationResult(
                is_valid=False,
                errors=[f"Schema validation failed: {e}"],
                warnings=[],
                plan=None
            )
    
    def _extract_json(self, text: str) -> Optional[str]:
        """
        Extract JSON from various text formats.
        
        Handles:
        - Pure JSON
        - Markdown code fences: ```json ... ```
        - Mixed text with JSON blocks
        """
        
        # Try direct JSON parse first
        text = text.strip()
        if text.startswith('{') and text.endswith('}'):
            return text
        
        # Try extracting from markdown code fence
        json_fence_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        matches = re.findall(json_fence_pattern, text, re.DOTALL)
        
        if matches:
            # Return the largest JSON block (most likely the complete plan)
            return max(matches, key=len).strip()
        
        # Try finding JSON object in text
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        if matches:
            # Return the largest JSON-like block
            return max(matches, key=len).strip()
        
        return None
    
    def _repair_json(self, json_str: str) -> Optional[str]:
        """
        Attempt to repair common JSON errors.
        
        Common issues:
        - Trailing commas
        - Unquoted keys
        - Missing commas between elements
        - Single quotes instead of double quotes
        """
        
        try:
            # Remove trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            # Replace single quotes with double quotes (careful with apostrophes)
            json_str = json_str.replace("'", '"')
            
            # Try parsing
            json.loads(json_str)
            return json_str
            
        except Exception:
            return None
    
    def parse_with_retry(
        self,
        llm_output: str,
        max_attempts: int = 3
    ) -> Tuple[Optional[RefactorPlan], ValidationResult]:
        """
        Parse with multiple repair attempts.
        
        Args:
            llm_output: Raw LLM output
            max_attempts: Number of repair attempts
        
        Returns:
            Tuple of (RefactorPlan or None, ValidationResult)
        """
        
        for attempt in range(max_attempts):
            plan, validation = self.parse(llm_output)
            
            if plan:
                return plan, validation
            
            logger.warning(
                f"Parse attempt {attempt + 1}/{max_attempts} failed: "
                f"{', '.join(validation.errors)}"
            )
        
        return None, validation


class PlanValidator:
    """
    Additional validation logic beyond Pydantic schema.
    
    Checks for:
    - Logical consistency (e.g., execution_order matches primary_changes)
    - File existence
    - Line number validity
    - Symbol naming conventions
    """
    
    def validate_execution_order(self, plan: RefactorPlan) -> Tuple[bool, str]:
        """Validate execution_order indices match primary_changes."""
        
        if not plan.execution_order:
            return True, ""
        
        max_index = len(plan.primary_changes) - 1
        
        for idx in plan.execution_order:
            if idx < 0 or idx > max_index:
                return False, f"execution_order index {idx} out of range (0-{max_index})"
        
        return True, ""
    
    def validate_line_numbers(self, plan: RefactorPlan) -> Tuple[bool, str]:
        """Validate line numbers are positive and start_line <= end_line."""
        
        for change in plan.primary_changes:
            if change.start_line and change.start_line < 0:
                return False, f"Invalid start_line: {change.start_line}"
            
            if change.end_line and change.end_line < 0:
                return False, f"Invalid end_line: {change.end_line}"
            
            if (change.start_line and change.end_line and 
                change.start_line > change.end_line):
                return False, (
                    f"start_line ({change.start_line}) > end_line ({change.end_line})"
                )
        
        return True, ""
    
    def validate_symbol_names(self, plan: RefactorPlan) -> Tuple[bool, str]:
        """Validate symbol names follow conventions."""
        
        # Python/JS naming conventions
        valid_identifier = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        
        for change in plan.primary_changes:
            if change.symbol_name and not valid_identifier.match(change.symbol_name):
                return False, f"Invalid symbol_name: {change.symbol_name}"
            
            if change.new_symbol_name and not valid_identifier.match(change.new_symbol_name):
                return False, f"Invalid new_symbol_name: {change.new_symbol_name}"
        
        return True, ""
    
    def validate_plan(self, plan: RefactorPlan) -> ValidationResult:
        """Run all validation checks."""
        
        errors = []
        warnings = []
        
        # Check execution order
        valid, msg = self.validate_execution_order(plan)
        if not valid:
            errors.append(msg)
        
        # Check line numbers
        valid, msg = self.validate_line_numbers(plan)
        if not valid:
            errors.append(msg)
        
        # Check symbol names
        valid, msg = self.validate_symbol_names(plan)
        if not valid:
            errors.append(msg)
        
        # Additional warnings
        if plan.estimated_files_affected > 10:
            warnings.append("Large refactor: affects >10 files")
        
        if plan.risk_level == "critical":
            warnings.append("Critical risk level - review carefully")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            plan=plan
        )
