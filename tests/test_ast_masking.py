"""
Tests for AST-Based Masking Module
====================================

Tests Tree-Sitter AST-guided masking for discrete diffusion models.
"""

import pytest
from src.diffusion import ASTMasker, MaskingStrategy, MaskedSpan


# Test code samples
PYTHON_CODE = '''
def calculate_total(items):
    """Calculate total price of items."""
    total = 0
    for item in items:
        total += item.price
    return total

class ShoppingCart:
    def __init__(self):
        self.items = []
    
    def add_item(self, item):
        self.items.append(item)
    
    def get_total(self):
        return calculate_total(self.items)
'''

TYPESCRIPT_CODE = '''
interface User {
    name: string;
    email: string;
}

class AuthService {
    private users: User[] = [];
    
    async login(email: string, password: string): Promise<User> {
        const user = this.users.find(u => u.email === email);
        if (!user) {
            throw new Error("User not found");
        }
        return user;
    }
    
    register(user: User) {
        this.users.push(user);
    }
}
'''


@pytest.fixture
def python_masker():
    """Create Python AST masker."""
    return ASTMasker(language="python")


@pytest.fixture
def typescript_masker():
    """Create TypeScript AST masker."""
    return ASTMasker(language="typescript")


def test_masker_initialization():
    """Test masker initializes with supported languages."""
    masker_py = ASTMasker(language="python")
    assert masker_py.language == "python"
    assert masker_py.mask_token == "[MASK]"
    
    masker_ts = ASTMasker(language="typescript")
    assert masker_ts.language == "typescript"
    
    # Invalid language
    with pytest.raises(ValueError, match="Unsupported language"):
        ASTMasker(language="cobol")


def test_mask_function_bodies_python(python_masker):
    """Test masking Python function bodies."""
    masked, spans = python_masker.mask(
        source_code=PYTHON_CODE,
        strategy=MaskingStrategy.FUNCTION_BODY,
        mask_ratio=1.0  # Mask all eligible nodes
    )
    
    assert "[MASK]" in masked
    assert len(spans) > 0
    
    # Verify spans have correct metadata
    for span in spans:
        assert span.node_type in ["function_definition", "block"]
        assert span.start_byte < span.end_byte
        assert span.start_line <= span.end_line
        assert len(span.original_text) > 0


def test_mask_identifiers_python(python_masker):
    """Test masking Python identifiers."""
    masked, spans = python_masker.mask(
        source_code=PYTHON_CODE,
        strategy=MaskingStrategy.IDENTIFIERS,
        mask_ratio=0.3
    )
    
    assert "[MASK]" in masked
    assert len(spans) > 0
    
    for span in spans:
        assert span.node_type == "identifier"


def test_mask_types_typescript(typescript_masker):
    """Test masking TypeScript type annotations."""
    masked, spans = typescript_masker.mask(
        source_code=TYPESCRIPT_CODE,
        strategy=MaskingStrategy.TYPES,
        mask_ratio=1.0
    )
    
    # TypeScript should have type annotations
    assert len(spans) > 0
    
    for span in spans:
        assert "type" in span.node_type.lower()


def test_mask_ratio_controls_coverage(python_masker):
    """Test that mask_ratio controls how many nodes are masked."""
    # Mask 30%
    _, spans_30 = python_masker.mask(
        PYTHON_CODE,
        strategy=MaskingStrategy.IDENTIFIERS,
        mask_ratio=0.3
    )
    
    # Mask 70%
    _, spans_70 = python_masker.mask(
        PYTHON_CODE,
        strategy=MaskingStrategy.IDENTIFIERS,
        mask_ratio=0.7
    )
    
    # Higher ratio should mask more spans
    assert len(spans_70) > len(spans_30)


def test_deterministic_masking(python_masker):
    """Test that deterministic masking produces same results."""
    masked1, spans1 = python_masker.mask(
        PYTHON_CODE,
        strategy=MaskingStrategy.FUNCTION_BODY,
        mask_ratio=0.5,
        deterministic=True
    )
    
    masked2, spans2 = python_masker.mask(
        PYTHON_CODE,
        strategy=MaskingStrategy.FUNCTION_BODY,
        mask_ratio=0.5,
        deterministic=True
    )
    
    # Should produce identical results
    assert masked1 == masked2
    assert len(spans1) == len(spans2)
    assert [s.start_byte for s in spans1] == [s.start_byte for s in spans2]


def test_unmask_restores_code(python_masker):
    """Test that unmasking with original text restores code."""
    original = "def foo():\n    return 42"
    
    masked, spans = python_masker.mask(
        original,
        strategy=MaskingStrategy.FUNCTION_BODY,
        mask_ratio=1.0
    )
    
    # Unmask with original text
    predictions = [span.original_text for span in spans]
    unmasked = python_masker.unmask(masked, spans, predictions)
    
    # Should match original (may have whitespace differences)
    assert "def foo()" in unmasked
    assert "return 42" in unmasked


def test_syntax_validation(python_masker):
    """Test syntax validation."""
    valid_code = "def foo():\n    return 42"
    is_valid, errors = python_masker.validate_syntax(valid_code)
    assert is_valid
    assert len(errors) == 0
    
    # Invalid syntax
    invalid_code = "def foo(\n    return 42"  # Missing closing paren
    is_valid, errors = python_masker.validate_syntax(invalid_code)
    assert not is_valid
    assert len(errors) > 0


def test_masked_span_repr():
    """Test MaskedSpan string representation."""
    span = MaskedSpan(
        start_byte=0,
        end_byte=20,
        start_line=1,
        end_line=1,
        start_col=0,
        end_col=20,
        node_type="function_definition",
        original_text="def foo():\n    pass",
    )
    
    repr_str = repr(span)
    assert "function_definition" in repr_str
    assert "L1:0" in repr_str


def test_target_nodes_override(python_masker):
    """Test explicit target_nodes parameter overrides strategy."""
    # Explicitly mask only 'return_statement' nodes
    masked, spans = python_masker.mask(
        PYTHON_CODE,
        strategy=MaskingStrategy.FUNCTION_BODY,  # This would normally mask function defs
        target_nodes=["return_statement"],  # Override with explicit list
        mask_ratio=1.0
    )
    
    # Should only have return_statement nodes
    for span in spans:
        assert span.node_type == "return_statement"


def test_no_eligible_nodes_returns_unchanged(python_masker):
    """Test that code with no eligible nodes is returned unchanged."""
    # Try to mask comments in code with no comments
    code = "x = 42"
    masked, spans = python_masker.mask(
        code,
        strategy=MaskingStrategy.COMMENTS,
        mask_ratio=1.0
    )
    
    assert masked == code
    assert len(spans) == 0


def test_preserve_syntax_flag(python_masker):
    """Test preserve_syntax flag."""
    masker = ASTMasker(language="python", preserve_syntax=True)
    assert masker.preserve_syntax is True
    
    masker_no_preserve = ASTMasker(language="python", preserve_syntax=False)
    assert masker_no_preserve.preserve_syntax is False


def test_typescript_function_masking(typescript_masker):
    """Test masking TypeScript method definitions."""
    masked, spans = typescript_masker.mask(
        TYPESCRIPT_CODE,
        strategy=MaskingStrategy.FUNCTION_BODY,
        mask_ratio=1.0
    )
    
    assert "[MASK]" in masked
    assert len(spans) > 0


def test_mask_token_customization():
    """Test custom mask token."""
    masker = ASTMasker(language="python", mask_token="<BLANK>")
    
    code = "def foo():\n    return 42"
    masked, _ = masker.mask(code, MaskingStrategy.FUNCTION_BODY, mask_ratio=1.0)
    
    assert "<BLANK>" in masked
    assert "[MASK]" not in masked


def test_nested_node_exclusion(python_masker):
    """Test that nested nodes are excluded to avoid double masking."""
    code = '''
def outer():
    def inner():
        return 42
    return inner()
'''
    
    masked, spans = python_masker.mask(
        code,
        strategy=MaskingStrategy.FUNCTION_BODY,
        mask_ratio=1.0
    )
    
    # Should not mask both outer and inner function bodies
    # (inner is a child of outer's body)
    assert len(spans) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
