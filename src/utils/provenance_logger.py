"""
Phase 5: Provenance Logger - Auditability and Traceability

This module provides comprehensive logging of code generation provenance.
Every code change is tracked with metadata about:
- Which models were used
- What operations were performed
- When and why changes were made
- Validation and safety checks performed

This is critical for the "Auditability" claim in the Ouroboros thesis.

Architecture:
    Generation Process → Provenance Logger → artifact_metadata.json

The logger tracks:
1. Model usage (Reasoner, Compressor, Generator)
2. Generation parameters (config, tokens, etc.)
3. Validation results
4. Safety checks
5. File modifications
6. Timestamps and durations

Created: 2025-12-21 (Phase 5 implementation)
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import json
import hashlib


@dataclass
class ModelUsage:
    """
    Tracks which model was used for what purpose.
    
    Attributes:
        phase: Phase name (reasoner, compressor, generator)
        model_name: Name of the model (e.g., "claude-3.5-sonnet", "jamba-1.5-mini")
        purpose: What the model did (e.g., "planning", "compression", "generation")
        tokens_used: Approximate tokens used
        duration_ms: Time taken in milliseconds
        metadata: Additional model-specific metadata
    """
    phase: str
    model_name: str
    purpose: str
    tokens_used: int = 0
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetyCheck:
    """
    Tracks safety validation performed.
    
    Attributes:
        check_type: Type of check (syntax, semantic, security, etc.)
        passed: Whether check passed
        details: Details about the check
        timestamp: When check was performed
    """
    check_type: str
    passed: bool
    details: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FileModification:
    """
    Tracks changes made to a file.
    
    Attributes:
        file_path: Path to modified file
        original_hash: SHA256 hash of original content
        modified_hash: SHA256 hash of modified content
        lines_added: Number of lines added
        lines_removed: Number of lines removed
        backup_path: Path to backup file (if created)
        timestamp: When modification was made
    """
    file_path: str
    original_hash: str
    modified_hash: str
    lines_added: int
    lines_removed: int
    backup_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ProvenanceMetadata:
    """
    Complete provenance metadata for a code generation run.
    
    This is the artifact_metadata.json structure that gets saved
    alongside generated code.
    
    Attributes:
        run_id: Unique identifier for this generation run
        issue_description: What was being changed
        timestamp_start: When generation started
        timestamp_end: When generation ended
        duration_seconds: Total duration
        models_used: List of all models used
        safety_checks: List of all safety checks performed
        file_modifications: List of all file changes
        config: Configuration used
        success: Whether generation succeeded
        errors: List of errors encountered
        metadata: Additional metadata
    """
    run_id: str
    issue_description: str
    timestamp_start: str
    timestamp_end: str
    duration_seconds: float
    models_used: List[ModelUsage] = field(default_factory=list)
    safety_checks: List[SafetyCheck] = field(default_factory=list)
    file_modifications: List[FileModification] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, output_path: Path):
        """
        Save to JSON file.
        
        Args:
            output_path: Path to save artifact_metadata.json
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.to_json(), encoding="utf-8")


class ProvenanceLogger:
    """
    Logs provenance metadata for code generation runs.
    
    This is the "Auditability" component that tracks everything that happens
    during code generation. Every run produces an artifact_metadata.json file
    that documents:
    - What models were used (Reasoner, Compressor, Generator)
    - What safety checks were performed
    - What files were modified
    - When and why changes were made
    
    Usage:
        ```python
        logger = ProvenanceLogger(
            run_id="gen_20250121_123456",
            issue_description="Add caching to user service"
        )
        
        # Track model usage
        logger.log_model_usage(
            phase="reasoner",
            model_name="claude-3.5-sonnet",
            purpose="planning",
            tokens_used=1500,
            duration_ms=2500.0
        )
        
        # Track safety check
        logger.log_safety_check(
            check_type="syntax",
            passed=True,
            details="Validated with Tree-Sitter"
        )
        
        # Track file modification
        logger.log_file_modification(
            file_path="src/user_service.py",
            original_content="...",
            modified_content="...",
            lines_added=15,
            lines_removed=3
        )
        
        # Save metadata
        logger.finalize(success=True)
        logger.save("./artifacts/artifact_metadata.json")
        ```
    
    Attributes:
        metadata: Provenance metadata being tracked
        start_time: When logging started
    """
    
    def __init__(
        self,
        run_id: Optional[str] = None,
        issue_description: str = "",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize provenance logger.
        
        Args:
            run_id: Unique run ID (auto-generated if not provided)
            issue_description: Description of the task
            config: Configuration used
        """
        if run_id is None:
            run_id = self._generate_run_id()
        
        self.start_time = datetime.now()
        
        self.metadata = ProvenanceMetadata(
            run_id=run_id,
            issue_description=issue_description,
            timestamp_start=self.start_time.isoformat(),
            timestamp_end="",
            duration_seconds=0.0,
            config=config or {}
        )
    
    def log_model_usage(
        self,
        phase: str,
        model_name: str,
        purpose: str,
        tokens_used: int = 0,
        duration_ms: float = 0.0,
        **kwargs
    ):
        """
        Log model usage.
        
        Args:
            phase: Phase name (reasoner, compressor, generator)
            model_name: Model name (e.g., "claude-3.5-sonnet")
            purpose: What the model did
            tokens_used: Approximate tokens used
            duration_ms: Time taken
            **kwargs: Additional metadata
        """
        usage = ModelUsage(
            phase=phase,
            model_name=model_name,
            purpose=purpose,
            tokens_used=tokens_used,
            duration_ms=duration_ms,
            metadata=kwargs
        )
        
        self.metadata.models_used.append(usage)
    
    def log_safety_check(
        self,
        check_type: str,
        passed: bool,
        details: str
    ):
        """
        Log safety check.
        
        Args:
            check_type: Type of check (syntax, semantic, security, etc.)
            passed: Whether check passed
            details: Details about the check
        """
        check = SafetyCheck(
            check_type=check_type,
            passed=passed,
            details=details
        )
        
        self.metadata.safety_checks.append(check)
    
    def log_file_modification(
        self,
        file_path: str,
        original_content: str,
        modified_content: str,
        lines_added: int,
        lines_removed: int,
        backup_path: Optional[str] = None
    ):
        """
        Log file modification.
        
        Args:
            file_path: Path to modified file
            original_content: Original file content
            modified_content: Modified file content
            lines_added: Number of lines added
            lines_removed: Number of lines removed
            backup_path: Path to backup file
        """
        modification = FileModification(
            file_path=file_path,
            original_hash=self._hash_content(original_content),
            modified_hash=self._hash_content(modified_content),
            lines_added=lines_added,
            lines_removed=lines_removed,
            backup_path=backup_path
        )
        
        self.metadata.file_modifications.append(modification)
    
    def log_error(self, error: str):
        """
        Log an error.
        
        Args:
            error: Error message
        """
        self.metadata.errors.append(error)
        self.metadata.success = False
    
    def finalize(self, success: Optional[bool] = None):
        """
        Finalize logging and compute final metadata.
        
        Args:
            success: Override success status (auto-determined if not provided)
        """
        end_time = datetime.now()
        
        self.metadata.timestamp_end = end_time.isoformat()
        self.metadata.duration_seconds = (end_time - self.start_time).total_seconds()
        
        if success is not None:
            self.metadata.success = success
        
        # Compute summary statistics
        total_tokens = sum(m.tokens_used for m in self.metadata.models_used)
        total_model_time = sum(m.duration_ms for m in self.metadata.models_used)
        
        self.metadata.metadata.update({
            "total_tokens_used": total_tokens,
            "total_model_time_ms": total_model_time,
            "num_models_used": len(self.metadata.models_used),
            "num_safety_checks": len(self.metadata.safety_checks),
            "num_safety_checks_passed": sum(
                1 for c in self.metadata.safety_checks if c.passed
            ),
            "num_files_modified": len(self.metadata.file_modifications),
            "total_lines_added": sum(
                m.lines_added for m in self.metadata.file_modifications
            ),
            "total_lines_removed": sum(
                m.lines_removed for m in self.metadata.file_modifications
            ),
        })
    
    def save(self, output_path: Path):
        """
        Save provenance metadata to file.
        
        Args:
            output_path: Path to save artifact_metadata.json
        """
        self.metadata.save(output_path)
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:6]
        return f"gen_{timestamp}_{random_suffix}"
    
    def _hash_content(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("Provenance Logger - Phase 5 Auditability")
    print("=" * 80)
    
    # Create logger
    logger = ProvenanceLogger(
        issue_description="Add caching to user service for improved performance"
    )
    
    print(f"\nRun ID: {logger.metadata.run_id}")
    print(f"Started: {logger.metadata.timestamp_start}")
    
    # Simulate model usage tracking
    print("\nLogging model usage...")
    
    logger.log_model_usage(
        phase="reasoner",
        model_name="claude-3.5-sonnet",
        purpose="analyzing dependencies and creating refactor plan",
        tokens_used=1500,
        duration_ms=2500.0,
        api_endpoint="anthropic"
    )
    
    logger.log_model_usage(
        phase="compressor",
        model_name="jamba-1.5-mini",
        purpose="compressing context to fit within token limit",
        tokens_used=8192,
        duration_ms=1200.0,
        api_endpoint="ai21",
        compression_ratio=0.42
    )
    
    logger.log_model_usage(
        phase="generator",
        model_name="diffusion-model",
        purpose="generating refactored code",
        tokens_used=3500,
        duration_ms=5500.0,
        backbone="mock",
        num_steps=10
    )
    
    # Log safety checks
    print("Logging safety checks...")
    
    logger.log_safety_check(
        check_type="syntax_validation",
        passed=True,
        details="Validated with Tree-Sitter Python parser - no syntax errors found"
    )
    
    logger.log_safety_check(
        check_type="import_validation",
        passed=True,
        details="All imports are resolvable"
    )
    
    # Log file modification
    print("Logging file modifications...")
    
    original_code = "def get_user(id):\n    return db.query(id)\n"
    modified_code = "def get_user(id):\n    if id in cache:\n        return cache[id]\n    result = db.query(id)\n    cache[id] = result\n    return result\n"
    
    logger.log_file_modification(
        file_path="src/services/user_service.py",
        original_content=original_code,
        modified_content=modified_code,
        lines_added=4,
        lines_removed=1,
        backup_path="src/services/user_service.py.backup"
    )
    
    # Finalize
    print("Finalizing...")
    logger.finalize(success=True)
    
    # Display summary
    print("\n" + "=" * 80)
    print("PROVENANCE METADATA SUMMARY")
    print("=" * 80)
    print(f"Run ID: {logger.metadata.run_id}")
    print(f"Duration: {logger.metadata.duration_seconds:.2f}s")
    print(f"Success: {logger.metadata.success}")
    print(f"\nModels Used: {len(logger.metadata.models_used)}")
    for model in logger.metadata.models_used:
        print(f"  - {model.model_name} ({model.phase}): {model.tokens_used} tokens, {model.duration_ms:.0f}ms")
    
    print(f"\nSafety Checks: {len(logger.metadata.safety_checks)}")
    for check in logger.metadata.safety_checks:
        status = "✓" if check.passed else "✗"
        print(f"  {status} {check.check_type}: {check.details}")
    
    print(f"\nFile Modifications: {len(logger.metadata.file_modifications)}")
    for mod in logger.metadata.file_modifications:
        print(f"  - {mod.file_path}: +{mod.lines_added}/-{mod.lines_removed} lines")
    
    print(f"\nTotal Tokens: {logger.metadata.metadata['total_tokens_used']}")
    print(f"Total Model Time: {logger.metadata.metadata['total_model_time_ms']:.0f}ms")
    print(f"Total Lines Added: {logger.metadata.metadata['total_lines_added']}")
    print(f"Total Lines Removed: {logger.metadata.metadata['total_lines_removed']}")
    
    # Show JSON
    print("\n" + "=" * 80)
    print("JSON OUTPUT (artifact_metadata.json)")
    print("=" * 80)
    print(logger.metadata.to_json())
    
    # Save to file
    output_path = Path("./artifact_metadata_example.json")
    logger.save(output_path)
    print(f"\nSaved to: {output_path}")
