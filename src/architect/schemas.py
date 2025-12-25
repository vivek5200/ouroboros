"""
JSON Schema Validation for Phase 2 Diff Skeletons.
Defines Pydantic models for LLM output validation.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class RefactorOperation(str, Enum):
    """Supported refactoring operations."""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"
    MOVE = "move"
    EXTRACT = "extract"
    INLINE = "inline"


class ChangeType(str, Enum):
    """Types of code changes."""
    IMPORT = "import"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    PARAMETER = "parameter"


class FileChange(BaseModel):
    """Represents a change to a single file."""
    
    target_file: str = Field(
        ..., 
        description="Absolute or relative path to the target file"
    )
    operation: RefactorOperation = Field(
        ..., 
        description="Type of refactoring operation to perform"
    )
    change_type: ChangeType = Field(
        ..., 
        description="Type of code element being changed"
    )
    
    # Location information
    start_line: Optional[int] = Field(
        None, 
        description="Starting line number for the change (1-indexed)"
    )
    end_line: Optional[int] = Field(
        None, 
        description="Ending line number for the change (1-indexed)"
    )
    
    # Change details
    old_content: Optional[str] = Field(
        None, 
        description="Original content to be replaced (for MODIFY, DELETE)"
    )
    new_content: Optional[str] = Field(
        None, 
        description="New content to insert (for CREATE, MODIFY)"
    )
    
    # Metadata
    symbol_name: Optional[str] = Field(
        None, 
        description="Name of symbol being changed (class, function, variable)"
    )
    new_symbol_name: Optional[str] = Field(
        None, 
        description="New name for symbol (for RENAME operations)"
    )
    
    # Validation
    @validator('end_line')
    def end_line_must_be_after_start(cls, v, values):
        if v is not None and 'start_line' in values and values['start_line'] is not None:
            if v < values['start_line']:
                raise ValueError('end_line must be >= start_line')
        return v


class DependencyImpact(BaseModel):
    """Represents impact on dependent files."""
    
    affected_file: str = Field(
        ..., 
        description="Path to file affected by the refactor"
    )
    impact_type: Literal["import", "call", "inheritance"] = Field(
        ..., 
        description="Type of dependency impact"
    )
    required_changes: List[FileChange] = Field(
        default_factory=list,
        description="Changes required in this file due to refactor"
    )
    breaking_change: bool = Field(
        False, 
        description="Whether this is a breaking change"
    )


class RefactorPlan(BaseModel):
    """
    Complete refactoring plan with file changes and dependency analysis.
    This is the primary output format for Phase 2 LLM.
    """
    
    plan_id: str = Field(
        ..., 
        description="Unique identifier for this refactor plan"
    )
    description: str = Field(
        ..., 
        description="Human-readable description of the refactor"
    )
    
    # Primary changes
    primary_changes: List[FileChange] = Field(
        ..., 
        description="List of primary file changes to execute"
    )
    
    # Dependency analysis
    dependency_impacts: List[DependencyImpact] = Field(
        default_factory=list,
        description="Analysis of impact on dependent files"
    )
    
    # Execution order
    execution_order: List[int] = Field(
        default_factory=list,
        description="Indices of primary_changes in execution order"
    )
    
    # Risk assessment
    risk_level: Literal["low", "medium", "high", "critical"] = Field(
        "medium", 
        description="Risk level of this refactor"
    )
    estimated_files_affected: int = Field(
        0, 
        description="Estimated number of files that will be modified"
    )
    
    priority: int = Field(
        1,
        description="Priority of this refactor (higher is more important)"
    )
    
    # Rollback information
    rollback_plan: Optional[Dict[str, Any]] = Field(
        None,
        description="Information needed to rollback this refactor"
    )
    
    @validator('execution_order')
    def validate_execution_order(cls, v, values):
        if 'primary_changes' in values:
            max_index = len(values['primary_changes']) - 1
            for idx in v:
                if idx < 0 or idx > max_index:
                    raise ValueError(f'Execution order index {idx} out of range')
        return v


class DiffSkeleton(BaseModel):
    """
    Diff skeleton for LLM output validation.
    Lightweight representation for quick validation before full execution.
    """
    
    target_file: str = Field(
        ..., 
        description="Target file for this diff"
    )
    operation: RefactorOperation = Field(
        ..., 
        description="Operation to perform"
    )
    hunks: List[Dict[str, Any]] = Field(
        ...,
        description="List of diff hunks with line numbers and content"
    )
    
    @validator('hunks')
    def validate_hunks(cls, v):
        for hunk in v:
            required_keys = {'start_line', 'end_line', 'content'}
            if not required_keys.issubset(hunk.keys()):
                raise ValueError(f'Hunk must contain {required_keys}')
        return v


class ValidationResult(BaseModel):
    """Result of validating a refactor plan."""
    
    is_valid: bool = Field(
        ..., 
        description="Whether the plan passed validation"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of validation warnings"
    )
    graph_consistent: bool = Field(
        True,
        description="Whether plan maintains graph consistency"
    )


class ExecutionResult(BaseModel):
    """Result of executing a refactor plan."""
    
    plan_id: str = Field(
        ..., 
        description="ID of executed plan"
    )
    success: bool = Field(
        ..., 
        description="Whether execution succeeded"
    )
    files_modified: List[str] = Field(
        default_factory=list,
        description="List of files that were modified"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of execution errors"
    )
    rollback_available: bool = Field(
        False,
        description="Whether rollback is available"
    )


# ===== Example Usage =====

def create_example_refactor_plan() -> RefactorPlan:
    """Create an example refactor plan for testing."""
    return RefactorPlan(
        plan_id="refactor_001",
        description="Rename function 'old_name' to 'new_name' in user_service.py",
        primary_changes=[
            FileChange(
                target_file="src/user_service.py",
                operation=RefactorOperation.RENAME,
                change_type=ChangeType.FUNCTION,
                start_line=10,
                end_line=15,
                symbol_name="old_name",
                new_symbol_name="new_name",
                old_content="def old_name(param):",
                new_content="def new_name(param):"
            )
        ],
        dependency_impacts=[
            DependencyImpact(
                affected_file="src/api.py",
                impact_type="call",
                required_changes=[
                    FileChange(
                        target_file="src/api.py",
                        operation=RefactorOperation.MODIFY,
                        change_type=ChangeType.FUNCTION,
                        start_line=25,
                        end_line=25,
                        old_content="result = old_name(data)",
                        new_content="result = new_name(data)"
                    )
                ],
                breaking_change=False
            )
        ],
        execution_order=[0],
        risk_level="low",
        estimated_files_affected=2
    )


def validate_refactor_plan(plan: RefactorPlan) -> ValidationResult:
    """
    Validate a refactor plan for consistency and safety.
    
    Args:
        plan: RefactorPlan to validate
    
    Returns:
        ValidationResult with errors/warnings
    """
    errors = []
    warnings = []
    
    # Check execution order
    if not plan.execution_order:
        warnings.append("No execution order specified")
    
    # Check for breaking changes
    breaking_changes = [
        impact for impact in plan.dependency_impacts 
        if impact.breaking_change
    ]
    if breaking_changes:
        warnings.append(f"Plan contains {len(breaking_changes)} breaking changes")
    
    # Validate file paths
    for change in plan.primary_changes:
        if not change.target_file:
            errors.append("FileChange missing target_file")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        graph_consistent=True
    )
