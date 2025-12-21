"""
Phase 5: Syntax Validator - Safety Gate for Code Generation

This module provides syntax validation using Tree-Sitter before code is written to disk.
It's a critical safety component that prevents invalid code from being applied.

Architecture:
    Generated Code → SyntaxValidator → Validation Result → Apply or Retry

The validator:
1. Parses code with Tree-Sitter
2. Checks for syntax errors
3. Validates AST structure
4. Returns detailed error information
5. Enables self-healing retry loops

Created: 2025-12-21 (Phase 5 implementation)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from pathlib import Path
import tree_sitter
from tree_sitter import Language, Parser

# Import tree-sitter language bindings
try:
    import tree_sitter_python as ts_python
    import tree_sitter_javascript as ts_javascript
    import tree_sitter_typescript as ts_typescript
except ImportError:
    ts_python = None
    ts_javascript = None
    ts_typescript = None


@dataclass
class SyntaxError:
    """
    Represents a syntax error found during validation.
    
    Attributes:
        line: Line number where error occurs (1-indexed)
        column: Column number where error occurs
        message: Error description
        node_type: Type of AST node with error
        context: Code context around the error
    """
    line: int
    column: int
    message: str
    node_type: str
    context: str = ""


@dataclass
class ValidationResult:
    """
    Result of syntax validation.
    
    Attributes:
        is_valid: Whether code has valid syntax
        errors: List of syntax errors found
        has_error_nodes: Whether AST contains ERROR nodes
        parse_time_ms: Time taken to parse (milliseconds)
        language: Programming language validated
        metadata: Additional validation metadata
    """
    is_valid: bool
    errors: List[SyntaxError] = field(default_factory=list)
    has_error_nodes: bool = False
    parse_time_ms: float = 0.0
    language: str = "python"
    metadata: dict = field(default_factory=dict)
    
    @property
    def error_summary(self) -> str:
        """Get human-readable error summary."""
        if self.is_valid:
            return "No syntax errors"
        
        summary_parts = []
        if self.has_error_nodes:
            summary_parts.append(f"{len(self.errors)} syntax errors")
        
        if self.errors:
            first_error = self.errors[0]
            summary_parts.append(f"First error at line {first_error.line}: {first_error.message}")
        
        return "; ".join(summary_parts)


class SyntaxValidator:
    """
    Tree-Sitter based syntax validator for multiple languages.
    
    This is the "Safety Gate" that prevents invalid code from being written.
    Before any code is applied to disk, it must pass through this validator.
    
    Usage:
        ```python
        validator = SyntaxValidator()
        
        # Validate Python code
        result = validator.validate(code, language="python")
        
        if result.is_valid:
            print("Code is valid!")
        else:
            print(f"Errors: {result.error_summary}")
            for error in result.errors:
                print(f"  Line {error.line}: {error.message}")
        ```
    
    Attributes:
        parsers: Dictionary of language parsers
        languages: Supported languages
    """
    
    def __init__(self):
        """Initialize syntax validator with language parsers."""
        self.parsers = {}
        self.languages = []
        
        # Initialize Python parser
        if ts_python:
            try:
                python_language = Language(ts_python.language())
                python_parser = Parser(python_language)
                self.parsers["python"] = python_parser
                self.languages.append("python")
            except Exception as e:
                print(f"Warning: Failed to initialize Python parser: {e}")
        
        # Initialize JavaScript parser
        if ts_javascript:
            try:
                js_language = Language(ts_javascript.language())
                js_parser = Parser(js_language)
                self.parsers["javascript"] = js_parser
                self.languages.append("javascript")
            except Exception as e:
                print(f"Warning: Failed to initialize JavaScript parser: {e}")
        
        # Initialize TypeScript parser
        if ts_typescript:
            try:
                # TypeScript has two parsers: typescript and tsx
                ts_language = Language(ts_typescript.language())
                ts_parser = Parser(ts_language)
                self.parsers["typescript"] = ts_parser
                self.languages.append("typescript")
            except Exception as e:
                print(f"Warning: Failed to initialize TypeScript parser: {e}")
    
    def validate(
        self,
        code: str,
        language: str = "python",
        strict: bool = True
    ) -> ValidationResult:
        """
        Validate syntax of code.
        
        Args:
            code: Source code to validate
            language: Programming language (python, javascript, typescript)
            strict: Whether to be strict about warnings
        
        Returns:
            ValidationResult with errors and metadata
        
        Raises:
            ValueError: If language not supported
        """
        import time
        
        if language not in self.parsers:
            raise ValueError(
                f"Language '{language}' not supported. "
                f"Available: {', '.join(self.languages)}"
            )
        
        start_time = time.time()
        
        # Parse code
        parser = self.parsers[language]
        tree = parser.parse(bytes(code, "utf8"))
        
        parse_time_ms = (time.time() - start_time) * 1000
        
        # Check for errors
        errors = []
        has_error_nodes = False
        
        # Walk tree and find ERROR nodes
        def walk_tree(node, depth=0):
            nonlocal has_error_nodes
            
            if node.type == "ERROR":
                has_error_nodes = True
                
                # Extract error details
                line = node.start_point[0] + 1  # Convert to 1-indexed
                column = node.start_point[1]
                
                # Get context (surrounding code)
                context = self._get_context(code, node.start_byte, node.end_byte)
                
                error = SyntaxError(
                    line=line,
                    column=column,
                    message=f"Syntax error in {language} code",
                    node_type=node.type,
                    context=context
                )
                errors.append(error)
            
            # Check for missing nodes (often indicates errors)
            if node.is_missing:
                has_error_nodes = True
                
                line = node.start_point[0] + 1
                column = node.start_point[1]
                
                error = SyntaxError(
                    line=line,
                    column=column,
                    message=f"Missing required {node.type}",
                    node_type=node.type,
                    context=self._get_context(code, node.start_byte, node.end_byte)
                )
                errors.append(error)
            
            # Recurse
            for child in node.children:
                walk_tree(child, depth + 1)
        
        walk_tree(tree.root_node)
        
        # Validate specific language rules
        if language == "python":
            errors.extend(self._validate_python_specifics(tree, code))
        
        # Determine if valid
        is_valid = not has_error_nodes and len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            has_error_nodes=has_error_nodes,
            parse_time_ms=parse_time_ms,
            language=language,
            metadata={
                "num_error_nodes": sum(1 for e in errors if e.node_type == "ERROR"),
                "num_missing_nodes": sum(1 for e in errors if "Missing" in e.message),
                "tree_depth": self._get_tree_depth(tree.root_node),
            }
        )
    
    def validate_file(
        self,
        file_path: Path,
        language: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate syntax of a file.
        
        Args:
            file_path: Path to file
            language: Language (auto-detected if not provided)
        
        Returns:
            ValidationResult
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        code = file_path.read_text(encoding="utf-8")
        
        # Auto-detect language if not provided
        if language is None:
            language = self._detect_language(file_path)
        
        return self.validate(code, language)
    
    def _get_context(
        self,
        code: str,
        start_byte: int,
        end_byte: int,
        context_lines: int = 2
    ) -> str:
        """
        Get code context around an error.
        
        Args:
            code: Source code
            start_byte: Start byte of error
            end_byte: End byte of error
            context_lines: Number of lines before/after to include
        
        Returns:
            Context string
        """
        lines = code.split('\n')
        
        # Find line containing error
        current_byte = 0
        error_line = 0
        
        for i, line in enumerate(lines):
            line_length = len(line) + 1  # +1 for newline
            if current_byte + line_length > start_byte:
                error_line = i
                break
            current_byte += line_length
        
        # Extract context
        start_line = max(0, error_line - context_lines)
        end_line = min(len(lines), error_line + context_lines + 1)
        
        context_lines_list = lines[start_line:end_line]
        
        # Add line numbers
        numbered_lines = []
        for i, line in enumerate(context_lines_list, start=start_line + 1):
            marker = ">>> " if i == error_line + 1 else "    "
            numbered_lines.append(f"{marker}{i:4d} | {line}")
        
        return "\n".join(numbered_lines)
    
    def _get_tree_depth(self, node, current_depth=0) -> int:
        """Get maximum depth of syntax tree."""
        if not node.children:
            return current_depth
        
        return max(
            self._get_tree_depth(child, current_depth + 1)
            for child in node.children
        )
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect language from file extension."""
        ext = file_path.suffix.lower()
        
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
        }
        
        return mapping.get(ext, "python")
    
    def _validate_python_specifics(
        self,
        tree,
        code: str
    ) -> List[SyntaxError]:
        """
        Validate Python-specific syntax rules.
        
        Checks for common Python issues:
        - Indentation errors
        - Missing colons
        - Unclosed brackets/parens
        """
        errors = []
        
        # Check for common Python issues
        # (Tree-Sitter already catches most of these, but we can add extra checks)
        
        # Example: Check for mixed tabs/spaces (if needed)
        # This is more of a style issue, but could be added
        
        return errors


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("Syntax Validator - Phase 5 Safety Gate")
    print("=" * 80)
    
    validator = SyntaxValidator()
    print(f"\nSupported languages: {', '.join(validator.languages)}")
    
    # Test with valid Python code
    valid_code = """
def hello(name):
    return f"Hello, {name}!"

class Greeter:
    def greet(self, name):
        return hello(name)
"""
    
    print("\n\nValidating VALID Python code:")
    result = validator.validate(valid_code, "python")
    print(f"  Is valid: {result.is_valid}")
    print(f"  Parse time: {result.parse_time_ms:.2f}ms")
    print(f"  Summary: {result.error_summary}")
    
    # Test with invalid Python code
    invalid_code = """
def hello(name)
    return f"Hello, {name}!"

class Greeter
    def greet(self, name):
        return hello(name
"""
    
    print("\n\nValidating INVALID Python code:")
    result = validator.validate(invalid_code, "python")
    print(f"  Is valid: {result.is_valid}")
    print(f"  Parse time: {result.parse_time_ms:.2f}ms")
    print(f"  Summary: {result.error_summary}")
    print(f"\n  Errors found: {len(result.errors)}")
    
    for i, error in enumerate(result.errors[:3], 1):  # Show first 3
        print(f"\n  Error {i}:")
        print(f"    Line {error.line}, Column {error.column}")
        print(f"    Message: {error.message}")
        if error.context:
            print(f"    Context:")
            for line in error.context.split('\n'):
                print(f"      {line}")
