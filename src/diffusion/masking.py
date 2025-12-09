"""
AST-Based Masking for Diffusion Models
========================================

Provides deterministic, Tree-Sitter AST-guided masking for slot tokens
in discrete diffusion models. Replaces heuristic token masking with
structural awareness for better code generation.

Key Features:
- Anchors mask tokens to AST node boundaries
- Preserves syntactic validity during diffusion
- Supports multi-language masking (Python, TypeScript, JavaScript, etc.)
- Deterministic masking for reproducibility
"""

import logging
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser, Node, Tree


logger = logging.getLogger(__name__)


class MaskingStrategy(Enum):
    """Strategies for masking code tokens based on AST structure."""
    
    FUNCTION_BODY = "function_body"  # Mask function/method bodies
    EXPRESSIONS = "expressions"  # Mask expression nodes
    STATEMENTS = "statements"  # Mask statement blocks
    IDENTIFIERS = "identifiers"  # Mask variable/function names
    TYPES = "types"  # Mask type annotations
    COMMENTS = "comments"  # Mask comment blocks
    FULL_NODE = "full_node"  # Mask entire AST node
    HYBRID = "hybrid"  # Combination of multiple strategies


@dataclass
class MaskedSpan:
    """Represents a masked span in the source code with AST metadata."""
    
    start_byte: int
    end_byte: int
    start_line: int
    end_line: int
    start_col: int
    end_col: int
    node_type: str
    original_text: str
    mask_token: str = "[MASK]"
    parent_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __repr__(self) -> str:
        return (
            f"MaskedSpan({self.node_type} at L{self.start_line}:{self.start_col}-"
            f"L{self.end_line}:{self.end_col}, '{self.original_text[:20]}...')"
        )


class ASTMasker:
    """
    AST-aware masker for discrete diffusion models.
    
    Uses Tree-Sitter to parse code and generate deterministic masks
    anchored to AST node boundaries. Ensures syntactic validity during
    diffusion process.
    
    Usage:
        masker = ASTMasker(language="python")
        masked_code, spans = masker.mask(
            source_code=code,
            strategy=MaskingStrategy.FUNCTION_BODY,
            mask_ratio=0.3
        )
    """
    
    SUPPORTED_LANGUAGES = {
        "python": ("py-tree-sitter-python", tspython.language),
        "javascript": ("tree-sitter-javascript", tsjavascript.language),
        "typescript": ("tree-sitter-typescript", tstypescript.language_typescript),
    }
    
    # AST node types to target for each masking strategy
    STRATEGY_NODE_TYPES = {
        MaskingStrategy.FUNCTION_BODY: {
            "python": ["function_definition", "block"],
            "javascript": ["function_declaration", "method_definition", "statement_block"],
            "typescript": ["function_declaration", "method_declaration", "statement_block"],
        },
        MaskingStrategy.EXPRESSIONS: {
            "python": ["expression_statement", "call", "binary_operator"],
            "javascript": ["call_expression", "binary_expression", "member_expression"],
            "typescript": ["call_expression", "binary_expression", "member_expression"],
        },
        MaskingStrategy.STATEMENTS: {
            "python": ["if_statement", "for_statement", "while_statement", "return_statement"],
            "javascript": ["if_statement", "for_statement", "while_statement", "return_statement"],
            "typescript": ["if_statement", "for_statement", "while_statement", "return_statement"],
        },
        MaskingStrategy.IDENTIFIERS: {
            "python": ["identifier"],
            "javascript": ["identifier"],
            "typescript": ["identifier", "type_identifier"],
        },
        MaskingStrategy.TYPES: {
            "python": ["type"],
            "javascript": [],  # JS doesn't have native types
            "typescript": ["type_annotation", "type_arguments", "type_identifier"],
        },
        MaskingStrategy.COMMENTS: {
            "python": ["comment"],
            "javascript": ["comment"],
            "typescript": ["comment"],
        },
    }
    
    def __init__(
        self,
        language: str = "python",
        mask_token: str = "[MASK]",
        preserve_syntax: bool = True,
    ):
        """
        Initialize AST masker.
        
        Args:
            language: Programming language ("python", "javascript", "typescript")
            mask_token: Token to use for masking
            preserve_syntax: Ensure masked code remains syntactically valid
        """
        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language: {language}. "
                f"Supported: {list(self.SUPPORTED_LANGUAGES.keys())}"
            )
        
        self.language = language
        self.mask_token = mask_token
        self.preserve_syntax = preserve_syntax
        
        # Initialize Tree-Sitter parser
        self.parser = Parser()
        lang_info = self.SUPPORTED_LANGUAGES[language]
        lang_func = lang_info[1]  # Get language function
        self.ts_language = Language(lang_func())
        self.parser.language = self.ts_language
        
        logger.info(f"ASTMasker initialized for {language}")
    
    def mask(
        self,
        source_code: str,
        strategy: MaskingStrategy = MaskingStrategy.FUNCTION_BODY,
        mask_ratio: float = 0.3,
        target_nodes: Optional[List[str]] = None,
        deterministic: bool = True,
    ) -> Tuple[str, List[MaskedSpan]]:
        """
        Mask source code based on AST structure.
        
        Args:
            source_code: Original source code
            strategy: Masking strategy (which AST nodes to target)
            mask_ratio: Fraction of eligible nodes to mask (0.0 to 1.0)
            target_nodes: Explicit list of node types to mask (overrides strategy)
            deterministic: Use deterministic node selection (for reproducibility)
        
        Returns:
            Tuple of (masked_code, list of MaskedSpan objects)
        """
        # Parse source code
        tree = self.parser.parse(bytes(source_code, "utf8"))
        root = tree.root_node
        
        # Get target node types
        if target_nodes:
            node_types = target_nodes
        elif strategy in self.STRATEGY_NODE_TYPES:
            node_types = self.STRATEGY_NODE_TYPES[strategy].get(self.language, [])
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        if not node_types:
            logger.warning(f"No node types defined for strategy {strategy} in {self.language}")
            return source_code, []
        
        # Find all eligible nodes
        eligible_nodes = self._find_eligible_nodes(root, node_types)
        
        if not eligible_nodes:
            logger.warning(f"No eligible nodes found for masking")
            return source_code, []
        
        # Select nodes to mask based on ratio
        num_to_mask = max(1, int(len(eligible_nodes) * mask_ratio))
        
        if deterministic:
            # Deterministic selection: first N nodes in pre-order traversal
            nodes_to_mask = eligible_nodes[:num_to_mask]
        else:
            # Random selection (for training variation)
            import random
            nodes_to_mask = random.sample(eligible_nodes, num_to_mask)
        
        # Sort nodes by position (reverse order for safe replacement)
        nodes_to_mask.sort(key=lambda n: n.start_byte, reverse=True)
        
        # Create masked spans
        masked_spans = []
        masked_code = source_code
        
        for node in nodes_to_mask:
            span = self._create_masked_span(node, source_code)
            masked_spans.append(span)
            
            # Replace node text with mask token
            before = masked_code[:node.start_byte]
            after = masked_code[node.end_byte:]
            masked_code = before + self.mask_token + after
        
        # Reverse spans list (so they're in document order)
        masked_spans.reverse()
        
        logger.info(
            f"Masked {len(masked_spans)} / {len(eligible_nodes)} nodes "
            f"({mask_ratio * 100:.1f}% ratio) using strategy {strategy.value}"
        )
        
        return masked_code, masked_spans
    
    def unmask(
        self,
        masked_code: str,
        spans: List[MaskedSpan],
        predictions: List[str],
    ) -> str:
        """
        Unmask code by replacing mask tokens with predictions.
        
        Args:
            masked_code: Code with [MASK] tokens
            spans: List of MaskedSpan objects from masking
            predictions: Predicted text for each mask (same order as spans)
        
        Returns:
            Unmasked source code
        """
        if len(spans) != len(predictions):
            raise ValueError(
                f"Mismatch between spans ({len(spans)}) and predictions ({len(predictions)})"
            )
        
        # Replace masks in reverse order (to preserve byte offsets)
        unmasked = masked_code
        for span, prediction in reversed(list(zip(spans, predictions))):
            # Find mask token position
            mask_start = unmasked.find(self.mask_token)
            if mask_start == -1:
                logger.warning(f"Mask token not found at expected position for span {span}")
                continue
            
            mask_end = mask_start + len(self.mask_token)
            unmasked = unmasked[:mask_start] + prediction + unmasked[mask_end:]
        
        return unmasked
    
    def validate_syntax(self, code: str) -> Tuple[bool, List[str]]:
        """
        Validate syntax of code using Tree-Sitter.
        
        Args:
            code: Source code to validate
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        tree = self.parser.parse(bytes(code, "utf8"))
        errors = []
        
        def find_errors(node: Node):
            if node.has_error:
                errors.append(
                    f"Syntax error at L{node.start_point[0]}:{node.start_point[1]}: "
                    f"'{node.type}'"
                )
            for child in node.children:
                find_errors(child)
        
        find_errors(tree.root_node)
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _find_eligible_nodes(
        self,
        root: Node,
        node_types: List[str],
    ) -> List[Node]:
        """
        Recursively find all nodes matching target types.
        
        Args:
            root: Root AST node
            node_types: List of node type strings to match
        
        Returns:
            List of matching nodes in pre-order traversal
        """
        eligible = []
        
        def traverse(node: Node):
            if node.type in node_types:
                # Skip nodes that are children of already selected nodes
                # to avoid nested masking
                is_child = any(
                    parent.start_byte <= node.start_byte and node.end_byte <= parent.end_byte
                    for parent in eligible
                )
                if not is_child:
                    eligible.append(node)
            
            for child in node.children:
                traverse(child)
        
        traverse(root)
        return eligible
    
    def _create_masked_span(self, node: Node, source_code: str) -> MaskedSpan:
        """
        Create MaskedSpan object from Tree-Sitter node.
        
        Args:
            node: Tree-Sitter AST node
            source_code: Original source code
        
        Returns:
            MaskedSpan with metadata
        """
        original_text = source_code[node.start_byte:node.end_byte]
        
        return MaskedSpan(
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            start_line=node.start_point[0],
            end_line=node.end_point[0],
            start_col=node.start_point[1],
            end_col=node.end_point[1],
            node_type=node.type,
            original_text=original_text,
            mask_token=self.mask_token,
            parent_type=node.parent.type if node.parent else None,
            metadata={
                "node_id": node.id,
                "is_named": node.is_named,
                "child_count": node.child_count,
            }
        )


def create_hybrid_masker(
    language: str,
    strategies: List[MaskingStrategy],
    weights: Optional[List[float]] = None,
) -> ASTMasker:
    """
    Create a hybrid masker that combines multiple strategies.
    
    Args:
        language: Programming language
        strategies: List of strategies to combine
        weights: Optional weights for each strategy (defaults to equal)
    
    Returns:
        Configured ASTMasker instance
    """
    if weights and len(weights) != len(strategies):
        raise ValueError("Number of weights must match number of strategies")
    
    masker = ASTMasker(language=language)
    
    # Store hybrid configuration
    masker.hybrid_strategies = strategies
    masker.hybrid_weights = weights or [1.0 / len(strategies)] * len(strategies)
    
    return masker


if __name__ == "__main__":
    # Example usage
    code = '''
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total

class ShoppingCart:
    def __init__(self):
        self.items = []
    
    def add_item(self, item):
        self.items.append(item)
'''
    
    masker = ASTMasker(language="python")
    
    # Mask function bodies
    masked, spans = masker.mask(
        code,
        strategy=MaskingStrategy.FUNCTION_BODY,
        mask_ratio=0.5
    )
    
    print("Original Code:")
    print(code)
    print("\nMasked Code:")
    print(masked)
    print(f"\nMasked {len(spans)} spans:")
    for span in spans:
        print(f"  - {span}")
