"""
Semantic Analyzer - Enhanced Safety Gate for Logic Errors

This module provides semantic analysis using static type checkers (pyright/mypy)
to catch logic errors that syntax validation misses.

Architecture:
    Generated Code → SyntaxValidator → SemanticAnalyzer → Apply or Retry

The analyzer:
1. Runs pyright or mypy on generated code
2. Parses type checker output
3. Classifies issues by severity
4. Returns structured analysis results
5. Enables retry loops for logic errors

Created: 2025-12-25 (Safety Gate Enhancement)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import subprocess
import json
import tempfile
import re
from enum import Enum


class IssueSeverity(Enum):
    """Severity levels for semantic issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class SemanticIssue:
    """
    Represents a semantic issue found during analysis.
    
    Attributes:
        line: Line number where issue occurs (1-indexed)
        column: Column number where issue occurs
        message: Issue description
        severity: Issue severity (error/warning/info)
        rule: Type checker rule that triggered
        code: Error code (e.g., "name-defined", "type-arg")
    """
    line: int
    column: int
    message: str
    severity: IssueSeverity
    rule: str = ""
    code: str = ""


@dataclass
class SemanticResult:
    """
    Result of semantic analysis.
    
    Attributes:
        is_valid: Whether code passes semantic checks
        errors: List of semantic errors found
        warnings: List of semantic warnings found
        checker_used: Which type checker was used
        analysis_time_ms: Time taken to analyze (milliseconds)
        type_coverage: Percentage of code with type hints (0-100)
        metadata: Additional analysis metadata
    """
    is_valid: bool
    errors: List[SemanticIssue] = field(default_factory=list)
    warnings: List[SemanticIssue] = field(default_factory=list)
    checker_used: str = "none"
    analysis_time_ms: float = 0.0
    type_coverage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def error_summary(self) -> str:
        """Get human-readable error summary."""
        if self.is_valid:
            return "No semantic errors"
        
        parts = []
        if self.errors:
            parts.append(f"{len(self.errors)} semantic error(s)")
            first_error = self.errors[0]
            parts.append(f"Line {first_error.line}: {first_error.message}")
        
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s)")
        
        return "; ".join(parts)


class SemanticAnalyzer:
    """
    Static analysis-based semantic validator using pyright/mypy.
    
    This enhances the syntax validator by catching logic errors:
    - Undefined variables
    - Type mismatches
    - Invalid attribute access
    - Missing imports
    - Dead code
    
    Usage:
        ```python
        analyzer = SemanticAnalyzer()
        
        # Analyze Python code
        result = analyzer.analyze(code, language="python")
        
        if result.is_valid:
            print("Code is semantically valid!")
        else:
            print(f"Errors: {result.error_summary}")
            for error in result.errors:
                print(f"  Line {error.line}: {error.message}")
        ```
    
    Attributes:
        prefer_pyright: Whether to prefer pyright over mypy
        pyright_available: Whether pyright is installed
        mypy_available: Whether mypy is installed
    """
    
    def __init__(self, prefer_pyright: bool = True):
        """
        Initialize semantic analyzer.
        
        Args:
            prefer_pyright: Use pyright as primary checker (faster, stricter)
        """
        self.prefer_pyright = prefer_pyright
        self.pyright_available = self._check_pyright_available()
        self.mypy_available = self._check_mypy_available()
        
        if not self.pyright_available and not self.mypy_available:
            print("Warning: Neither pyright nor mypy is installed. Semantic analysis disabled.")
    
    def _check_pyright_available(self) -> bool:
        """Check if pyright is installed and available."""
        try:
            result = subprocess.run(
                ["pyright", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _check_mypy_available(self) -> bool:
        """Check if mypy is installed and available."""
        try:
            result = subprocess.run(
                ["mypy", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def analyze(
        self,
        code: str,
        language: str = "python",
        strict: bool = False
    ) -> SemanticResult:
        """
        Analyze code for semantic errors.
        
        Args:
            code: Source code to analyze
            language: Programming language (currently only "python" supported)
            strict: Enable strict type checking mode
        
        Returns:
            SemanticResult with errors and warnings
        """
        import time
        start_time = time.time()
        
        # Only Python is supported currently
        if language != "python":
            return SemanticResult(
                is_valid=True,
                checker_used="none",
                metadata={"reason": f"Language '{language}' not supported for semantic analysis"}
            )
        
        # Check if any type checker is available
        if not self.pyright_available and not self.mypy_available:
            return SemanticResult(
                is_valid=True,
                checker_used="none",
                metadata={"reason": "No type checker available"}
            )
        
        # Choose type checker
        if self.prefer_pyright and self.pyright_available:
            result = self._run_pyright(code, strict)
        elif self.mypy_available:
            result = self._run_mypy(code, strict)
        else:
            result = self._run_pyright(code, strict)
        
        # Calculate analysis time
        result.analysis_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    def _run_pyright(self, code: str, strict: bool) -> SemanticResult:
        """
        Run pyright type checker on code.
        
        Args:
            code: Source code to check
            strict: Enable strict mode
        
        Returns:
            SemanticResult with pyright findings
        """
        # Create temporary file for analysis
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            # Run pyright with JSON output
            cmd = [
                "pyright",
                "--outputjson",
                str(temp_path)
            ]
            
            if strict:
                cmd.append("--strict")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse JSON output
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                # Fallback to text parsing if JSON fails
                return self._parse_pyright_text(result.stdout, result.stderr)
            
            # Extract diagnostics
            errors = []
            warnings = []
            
            diagnostics = output.get("generalDiagnostics", [])
            for diag in diagnostics:
                issue = SemanticIssue(
                    line=diag.get("range", {}).get("start", {}).get("line", 0) + 1,
                    column=diag.get("range", {}).get("start", {}).get("character", 0),
                    message=diag.get("message", "Unknown error"),
                    severity=IssueSeverity.ERROR if diag.get("severity") == "error" else IssueSeverity.WARNING,
                    rule=diag.get("rule", ""),
                    code=diag.get("code", "")
                )
                
                if issue.severity == IssueSeverity.ERROR:
                    errors.append(issue)
                else:
                    warnings.append(issue)
            
            return SemanticResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                checker_used="pyright",
                metadata={"diagnostics_count": len(diagnostics)}
            )
        
        except subprocess.TimeoutExpired:
            return SemanticResult(
                is_valid=False,
                errors=[SemanticIssue(
                    line=0,
                    column=0,
                    message="Pyright analysis timed out",
                    severity=IssueSeverity.ERROR
                )],
                checker_used="pyright"
            )
        except Exception as e:
            return SemanticResult(
                is_valid=False,
                errors=[SemanticIssue(
                    line=0,
                    column=0,
                    message=f"Pyright analysis failed: {str(e)}",
                    severity=IssueSeverity.ERROR
                )],
                checker_used="pyright"
            )
        finally:
            # Cleanup temp file
            if temp_path.exists():
                temp_path.unlink()
    
    def _parse_pyright_text(self, stdout: str, stderr: str) -> SemanticResult:
        """Parse pyright text output as fallback."""
        errors = []
        warnings = []
        
        # Simple regex to extract errors from text output
        # Format: file.py:line:col - error: message
        pattern = r':(\d+):(\d+)\s+-\s+(error|warning):\s+(.+)'
        
        for line in (stdout + stderr).split('\n'):
            match = re.search(pattern, line)
            if match:
                line_num = int(match.group(1))
                col_num = int(match.group(2))
                severity_str = match.group(3)
                message = match.group(4)
                
                issue = SemanticIssue(
                    line=line_num,
                    column=col_num,
                    message=message,
                    severity=IssueSeverity.ERROR if severity_str == "error" else IssueSeverity.WARNING
                )
                
                if issue.severity == IssueSeverity.ERROR:
                    errors.append(issue)
                else:
                    warnings.append(issue)
        
        return SemanticResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            checker_used="pyright"
        )
    
    def _run_mypy(self, code: str, strict: bool) -> SemanticResult:
        """
        Run mypy type checker on code.
        
        Args:
            code: Source code to check
            strict: Enable strict mode
        
        Returns:
            SemanticResult with mypy findings
        """
        # Create temporary file for analysis
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            # Run mypy
            cmd = ["mypy", str(temp_path)]
            
            if strict:
                cmd.append("--strict")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse mypy output
            errors = []
            warnings = []
            
            # Format: file.py:line: error: message
            pattern = r':(\d+):\s+(error|warning|note):\s+(.+)'
            
            for line in result.stdout.split('\n'):
                match = re.search(pattern, line)
                if match:
                    line_num = int(match.group(1))
                    severity_str = match.group(2)
                    message = match.group(3)
                    
                    # Skip notes
                    if severity_str == "note":
                        continue
                    
                    issue = SemanticIssue(
                        line=line_num,
                        column=0,  # mypy doesn't always provide column
                        message=message,
                        severity=IssueSeverity.ERROR if severity_str == "error" else IssueSeverity.WARNING
                    )
                    
                    if issue.severity == IssueSeverity.ERROR:
                        errors.append(issue)
                    else:
                        warnings.append(issue)
            
            return SemanticResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                checker_used="mypy"
            )
        
        except subprocess.TimeoutExpired:
            return SemanticResult(
                is_valid=False,
                errors=[SemanticIssue(
                    line=0,
                    column=0,
                    message="Mypy analysis timed out",
                    severity=IssueSeverity.ERROR
                )],
                checker_used="mypy"
            )
        except Exception as e:
            return SemanticResult(
                is_valid=False,
                errors=[SemanticIssue(
                    line=0,
                    column=0,
                    message=f"Mypy analysis failed: {str(e)}",
                    severity=IssueSeverity.ERROR
                )],
                checker_used="mypy"
            )
        finally:
            # Cleanup temp file
            if temp_path.exists():
                temp_path.unlink()


# Example usage
if __name__ == "__main__":
    print("Semantic Analyzer - Enhanced Safety Gate")
    print("=" * 50)
    
    analyzer = SemanticAnalyzer()
    print(f"\nPyright available: {analyzer.pyright_available}")
    print(f"Mypy available: {analyzer.mypy_available}")
    
    # Test 1: Valid code
    print("\n\nTest 1: Valid code")
    print("-" * 50)
    valid_code = """
def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("Negative numbers not allowed")
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
"""
    result = analyzer.analyze(valid_code, "python")
    print(f"Valid: {result.is_valid}")
    print(f"Checker: {result.checker_used}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    
    # Test 2: Undefined variable
    print("\n\nTest 2: Undefined variable")
    print("-" * 50)
    undefined_code = """
def calculate():
    result = undefined_var + 1
    return result
"""
    result = analyzer.analyze(undefined_code, "python")
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {len(result.errors)}")
    if result.errors:
        for error in result.errors:
            print(f"  Line {error.line}: {error.message}")
    
    # Test 3: Type mismatch
    print("\n\nTest 3: Type mismatch")
    print("-" * 50)
    type_error_code = """
def add_numbers(a: int, b: int) -> int:
    return a + b

result: int = add_numbers("hello", "world")
"""
    result = analyzer.analyze(type_error_code, "python")
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {len(result.errors)}")
    if result.errors:
        for error in result.errors:
            print(f"  Line {error.line}: {error.message}")
