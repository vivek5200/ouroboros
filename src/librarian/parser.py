"""
Ouroboros - Code Parser Module
Uses Tree-sitter to parse source code and extract AST structures.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser, Node


@dataclass
class ImportStatement:
    """Represents an import/require statement."""
    source_file: str
    imported_symbols: List[str]
    is_default: bool
    line_number: int


@dataclass
class ClassDefinition:
    """Represents a class definition."""
    name: str
    fully_qualified_name: str
    start_line: int
    end_line: int
    is_exported: bool
    parent_classes: List[str]
    methods: List['FunctionDefinition']


@dataclass
class FunctionDefinition:
    """Represents a function/method definition."""
    name: str
    signature: str
    start_line: int
    end_line: int
    is_async: bool
    is_exported: bool
    parent_class: Optional[str]
    calls: List[str]  # Function names called within this function


class CodeParser:
    """
    Multi-language code parser using Tree-sitter.
    Extracts structural information for graph database ingestion.
    """
    
    SUPPORTED_LANGUAGES = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
    }
    
    def __init__(self):
        """Initialize parsers for supported languages."""
        self.parsers = {
            'python': self._create_parser(Language(tspython.language())),
            'javascript': self._create_parser(Language(tsjs.language())),
            'typescript': self._create_parser(Language(tsts.language_typescript())),
        }
    
    def _create_parser(self, language: Language) -> Parser:
        """Create a Tree-sitter parser for a language."""
        parser = Parser(language)
        return parser
    
    def detect_language(self, file_path: str) -> Optional[str]:
        """
        Detect language from file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language name or None if unsupported
        """
        ext = Path(file_path).suffix.lower()
        return self.SUPPORTED_LANGUAGES.get(ext)
    
    def parse_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse a source file and extract structural information.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Dictionary containing imports, classes, and functions
        """
        language = self.detect_language(file_path)
        if not language:
            return None
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            parser = self.parsers[language]
            tree = parser.parse(content)
            
            if language == 'python':
                return self._parse_python(tree, content.decode('utf-8'), file_path)
            elif language == 'javascript':
                return self._parse_javascript(tree, content.decode('utf-8'), file_path)
            elif language == 'typescript':
                return self._parse_typescript(tree, content.decode('utf-8'), file_path)
        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def _parse_python(self, tree, content: str, file_path: str) -> Dict[str, Any]:
        """Parse Python file."""
        root = tree.root_node
        lines = content.split('\n')
        
        return {
            'imports': self._extract_python_imports(root, lines),
            'classes': self._extract_python_classes(root, lines, file_path),
            'functions': self._extract_python_functions(root, lines, file_path),
        }
    
    def _parse_javascript(self, tree, content: str, file_path: str) -> Dict[str, Any]:
        """Parse JavaScript file."""
        root = tree.root_node
        lines = content.split('\n')
        
        return {
            'imports': self._extract_js_imports(root, lines),
            'classes': self._extract_js_classes(root, lines, file_path),
            'functions': self._extract_js_functions(root, lines, file_path),
        }
    
    def _parse_typescript(self, tree, content: str, file_path: str) -> Dict[str, Any]:
        """Parse TypeScript file."""
        # TypeScript shares most parsing logic with JavaScript
        return self._parse_javascript(tree, content, file_path)
    
    # ===== Python Extraction =====
    
    def _extract_python_imports(self, root: Node, lines: List[str]) -> List[ImportStatement]:
        """Extract import statements from Python AST."""
        imports = []
        
        def traverse(node: Node):
            if node.type == 'import_statement':
                # import module
                line_num = node.start_point[0]
                module_node = node.child_by_field_name('name')
                if module_node:
                    module_name = self._get_node_text(module_node, lines)
                    imports.append(ImportStatement(
                        source_file=module_name,
                        imported_symbols=[],
                        is_default=True,
                        line_number=line_num
                    ))
            
            elif node.type == 'import_from_statement':
                # from module import symbol
                line_num = node.start_point[0]
                module_node = node.child_by_field_name('module_name')
                if module_node:
                    module_name = self._get_node_text(module_node, lines)
                    symbols = []
                    for child in node.children:
                        if child.type == 'dotted_name' or child.type == 'identifier':
                            if child != module_node:
                                symbols.append(self._get_node_text(child, lines))
                    
                    imports.append(ImportStatement(
                        source_file=module_name,
                        imported_symbols=symbols,
                        is_default=False,
                        line_number=line_num
                    ))
            
            for child in node.children:
                traverse(child)
        
        traverse(root)
        return imports
    
    def _extract_python_classes(self, root: Node, lines: List[str], file_path: str) -> List[ClassDefinition]:
        """Extract class definitions from Python AST."""
        classes = []
        
        def traverse(node: Node, parent_path: str = ""):
            if node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    class_name = self._get_node_text(name_node, lines)
                    fqn = f"{parent_path}.{class_name}" if parent_path else class_name
                    
                    # Extract parent classes
                    parent_classes = []
                    superclasses_node = node.child_by_field_name('superclasses')
                    if superclasses_node:
                        for child in superclasses_node.children:
                            if child.type in ['identifier', 'attribute']:
                                parent_classes.append(self._get_node_text(child, lines))
                    
                    # Extract methods
                    methods = []
                    body = node.child_by_field_name('body')
                    if body:
                        for child in body.children:
                            if child.type == 'function_definition':
                                method = self._extract_python_function_node(child, lines, fqn)
                                if method:
                                    methods.append(method)
                    
                    classes.append(ClassDefinition(
                        name=class_name,
                        fully_qualified_name=fqn,
                        start_line=node.start_point[0],
                        end_line=node.end_point[0],
                        is_exported=True,  # Python doesn't have explicit exports
                        parent_classes=parent_classes,
                        methods=methods
                    ))
            
            for child in node.children:
                traverse(child, parent_path)
        
        traverse(root)
        return classes
    
    def _extract_python_functions(self, root: Node, lines: List[str], file_path: str) -> List[FunctionDefinition]:
        """Extract top-level function definitions from Python AST."""
        functions = []
        
        for child in root.children:
            if child.type == 'function_definition':
                func = self._extract_python_function_node(child, lines, None)
                if func:
                    functions.append(func)
        
        return functions
    
    def _extract_python_function_node(self, node: Node, lines: List[str], parent_class: Optional[str]) -> Optional[FunctionDefinition]:
        """Extract a single Python function node."""
        name_node = node.child_by_field_name('name')
        if not name_node:
            return None
        
        func_name = self._get_node_text(name_node, lines)
        
        # Build signature
        params_node = node.child_by_field_name('parameters')
        params_text = self._get_node_text(params_node, lines) if params_node else "()"
        signature = f"{func_name}{params_text}"
        
        # Check if async
        is_async = any(child.type == 'async' for child in node.children)
        
        # Extract function calls
        calls = self._extract_python_function_calls(node, lines)
        
        return FunctionDefinition(
            name=func_name,
            signature=signature,
            start_line=node.start_point[0],
            end_line=node.end_point[0],
            is_async=is_async,
            is_exported=True,
            parent_class=parent_class,
            calls=calls
        )
    
    # ===== JavaScript/TypeScript Extraction =====
    
    def _extract_js_imports(self, root: Node, lines: List[str]) -> List[ImportStatement]:
        """Extract import/require statements from JS/TS AST."""
        imports = []
        
        def traverse(node: Node):
            # ES6 import
            if node.type == 'import_statement':
                line_num = node.start_point[0]
                source_node = None
                symbols = []
                is_default = False
                
                for child in node.children:
                    if child.type == 'string':
                        source_node = child
                    elif child.type == 'import_clause':
                        for subchild in child.children:
                            if subchild.type == 'identifier':
                                is_default = True
                                symbols.append(self._get_node_text(subchild, lines))
                            elif subchild.type == 'named_imports':
                                for spec in subchild.children:
                                    if spec.type == 'import_specifier':
                                        name = spec.child_by_field_name('name')
                                        if name:
                                            symbols.append(self._get_node_text(name, lines))
                
                if source_node:
                    source = self._get_node_text(source_node, lines).strip('"\'')
                    imports.append(ImportStatement(
                        source_file=source,
                        imported_symbols=symbols,
                        is_default=is_default,
                        line_number=line_num
                    ))
            
            # CommonJS require
            elif node.type == 'variable_declaration':
                for child in node.children:
                    if child.type == 'variable_declarator':
                        init = child.child_by_field_name('value')
                        if init and init.type == 'call_expression':
                            func = init.child_by_field_name('function')
                            if func and self._get_node_text(func, lines) == 'require':
                                args = init.child_by_field_name('arguments')
                                if args:
                                    for arg in args.children:
                                        if arg.type == 'string':
                                            source = self._get_node_text(arg, lines).strip('"\'')
                                            imports.append(ImportStatement(
                                                source_file=source,
                                                imported_symbols=[],
                                                is_default=True,
                                                line_number=node.start_point[0]
                                            ))
            
            for child in node.children:
                traverse(child)
        
        traverse(root)
        return imports
    
    def _extract_js_classes(self, root: Node, lines: List[str], file_path: str) -> List[ClassDefinition]:
        """Extract class definitions from JS/TS AST."""
        classes = []
        
        def traverse(node: Node):
            if node.type == 'class_declaration' or node.type == 'class':
                name_node = node.child_by_field_name('name')
                if name_node:
                    class_name = self._get_node_text(name_node, lines)
                    
                    # Check if exported
                    parent = node.parent
                    is_exported = parent and parent.type == 'export_statement'
                    
                    # Extract parent class
                    parent_classes = []
                    heritage = node.child_by_field_name('heritage')
                    if heritage:
                        for child in heritage.children:
                            if child.type == 'extends_clause':
                                parent_node = child.child_by_field_name('value')
                                if parent_node:
                                    parent_classes.append(self._get_node_text(parent_node, lines))
                    
                    # Extract methods
                    methods = []
                    body = node.child_by_field_name('body')
                    if body:
                        for child in body.children:
                            if child.type == 'method_definition':
                                method = self._extract_js_method_node(child, lines, class_name)
                                if method:
                                    methods.append(method)
                    
                    classes.append(ClassDefinition(
                        name=class_name,
                        fully_qualified_name=class_name,
                        start_line=node.start_point[0],
                        end_line=node.end_point[0],
                        is_exported=is_exported,
                        parent_classes=parent_classes,
                        methods=methods
                    ))
            
            for child in node.children:
                traverse(child)
        
        traverse(root)
        return classes
    
    def _extract_js_functions(self, root: Node, lines: List[str], file_path: str) -> List[FunctionDefinition]:
        """Extract function definitions from JS/TS AST."""
        functions = []
        
        def traverse(node: Node):
            if node.type in ['function_declaration', 'arrow_function', 'function']:
                func = self._extract_js_function_node(node, lines, None)
                if func:
                    # Check if exported
                    parent = node.parent
                    if parent and parent.type == 'export_statement':
                        func.is_exported = True
                    functions.append(func)
            
            for child in node.children:
                traverse(child)
        
        traverse(root)
        return functions
    
    def _extract_js_function_node(self, node: Node, lines: List[str], parent_class: Optional[str]) -> Optional[FunctionDefinition]:
        """Extract a single JS/TS function node."""
        name_node = node.child_by_field_name('name')
        func_name = self._get_node_text(name_node, lines) if name_node else '<anonymous>'
        
        # Build signature
        params_node = node.child_by_field_name('parameters')
        params_text = self._get_node_text(params_node, lines) if params_node else "()"
        signature = f"{func_name}{params_text}"
        
        # Check if async
        is_async = any(child.type == 'async' for child in node.children)
        
        # Extract function calls from body
        calls = self._extract_js_function_calls(node, lines)
        
        return FunctionDefinition(
            name=func_name,
            signature=signature,
            start_line=node.start_point[0],
            end_line=node.end_point[0],
            is_async=is_async,
            is_exported=False,
            parent_class=parent_class,
            calls=calls
        )
    
    def _extract_js_method_node(self, node: Node, lines: List[str], parent_class: str) -> Optional[FunctionDefinition]:
        """Extract a class method from JS/TS AST."""
        name_node = node.child_by_field_name('name')
        if not name_node:
            return None
        
        method_name = self._get_node_text(name_node, lines)
        
        # Build signature
        params_node = node.child_by_field_name('parameters')
        params_text = self._get_node_text(params_node, lines) if params_node else "()"
        signature = f"{parent_class}.{method_name}{params_text}"
        
        # Check if async
        is_async = any(child.type == 'async' for child in node.children)
        
        # Extract function calls from body
        calls = self._extract_js_function_calls(node, lines)
        
        return FunctionDefinition(
            name=method_name,
            signature=signature,
            start_line=node.start_point[0],
            end_line=node.end_point[0],
            is_async=is_async,
            is_exported=False,
            parent_class=parent_class,
            calls=calls
        )
    
    # ===== Call Graph Extraction =====
    
    def _extract_python_function_calls(self, node: Node, lines: List[str]) -> List[str]:
        """
        Extract function calls from a Python function body.
        Uses fuzzy matching - captures function name only, ignoring arguments.
        """
        calls = []
        
        def traverse(n: Node):
            if n.type == 'call':
                # Get function name
                func_node = n.child_by_field_name('function')
                if func_node:
                    if func_node.type == 'identifier':
                        # Simple function call: foo()
                        call_name = self._get_node_text(func_node, lines)
                        calls.append(call_name)
                    elif func_node.type == 'attribute':
                        # Method call: obj.method()
                        # Get the method name only (rightmost identifier)
                        attr_node = func_node.child_by_field_name('attribute')
                        if attr_node:
                            call_name = self._get_node_text(attr_node, lines)
                            calls.append(call_name)
            
            # Recurse through children
            for child in n.children:
                traverse(child)
        
        # Start traversal from function body
        body = node.child_by_field_name('body')
        if body:
            traverse(body)
        
        return calls
    
    def _extract_js_function_calls(self, node: Node, lines: List[str]) -> List[str]:
        """
        Extract function calls from a JavaScript/TypeScript function body.
        Uses fuzzy matching - captures function name only, ignoring arguments.
        """
        calls = []
        
        def traverse(n: Node):
            if n.type == 'call_expression':
                # Get function name
                func_node = n.child_by_field_name('function')
                if func_node:
                    if func_node.type == 'identifier':
                        # Simple function call: foo()
                        call_name = self._get_node_text(func_node, lines)
                        calls.append(call_name)
                    elif func_node.type == 'member_expression':
                        # Method call: obj.method()
                        # Get the property name only (rightmost identifier)
                        prop_node = func_node.child_by_field_name('property')
                        if prop_node:
                            call_name = self._get_node_text(prop_node, lines)
                            calls.append(call_name)
            
            # Recurse through children
            for child in n.children:
                traverse(child)
        
        # Start traversal from function body
        body = node.child_by_field_name('body')
        if body:
            traverse(body)
        
        return calls
    
    # ===== Utility Methods =====
    
    def _get_node_text(self, node: Node, lines: List[str]) -> str:
        """Extract text content from a Tree-sitter node."""
        start_row, start_col = node.start_point
        end_row, end_col = node.end_point
        
        if start_row == end_row:
            return lines[start_row][start_col:end_col]
        
        text_lines = [lines[start_row][start_col:]]
        text_lines.extend(lines[start_row + 1:end_row])
        text_lines.append(lines[end_row][:end_col])
        
        return '\n'.join(text_lines)
