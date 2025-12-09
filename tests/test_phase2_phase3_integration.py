"""
Integration test for Phase 2 Reasoner + Phase 3 Context Encoder
=================================================================

Tests the integration between Reasoner and ContextEncoder.
"""

import pytest
from unittest.mock import Mock, patch
from src.reasoner import Reasoner, ReasonerConfig
from src.reasoner.config import LLMProvider
from src.librarian.context_serializer import CompressedContextBlock


@pytest.fixture
def mock_reasoner():
    """Create a reasoner with mocked LLM client."""
    config = ReasonerConfig(provider=LLMProvider.MOCK)
    reasoner = Reasoner(config)
    return reasoner


@pytest.fixture
def mock_graph_context():
    """Mock context from GraphRetriever."""
    return {
        "file_path": "src/auth/login.ts",
        "imports": ["{ User } from '../models/user'", "{ Firebase } from '../lib/firebase'"],
        "classes": [
            {
                "name": "LoginService",
                "methods": [
                    {"name": "loginWithFirebase"},
                    {"name": "logout"}
                ]
            }
        ],
        "functions": [],
        "content": """
export class LoginService {
    async loginWithFirebase(email: string, password: string) {
        // Implementation
    }
}
"""
    }


def test_reasoner_has_encoder(mock_reasoner):
    """Test that Reasoner has Context Encoder initialized."""
    assert mock_reasoner.encoder is not None
    assert hasattr(mock_reasoner.encoder, 'compress')


def test_reasoner_has_serializer(mock_reasoner):
    """Test that Reasoner still has serializer for backward compatibility."""
    assert mock_reasoner.serializer is not None


def test_context_to_raw_string(mock_reasoner, mock_graph_context):
    """Test conversion of graph context to raw string."""
    raw_string = mock_reasoner._context_to_raw_string(mock_graph_context)
    
    assert "# File: src/auth/login.ts" in raw_string
    assert "{ User }" in raw_string
    assert "LoginService" in raw_string
    assert "loginWithFirebase" in raw_string


@patch.object(Reasoner, '_retrieve_context')
def test_generate_refactor_plan_without_deep_context(mock_retrieve, mock_reasoner):
    """Test standard refactor plan generation (Phase 2 only)."""
    # Mock context retrieval
    mock_retrieve.return_value = [
        CompressedContextBlock(
            block_id="mock_1",
            block_type="file",
            content="# Mock context",
            format="markdown",
            token_count=100
        )
    ]
    
    # Mock LLM response
    mock_reasoner.llm_client.generate = Mock(return_value=Mock(
        content='{"plan_id": "test", "files": [], "dependencies": [], "estimated_impact": "low"}',
        output_tokens=50,
        cost_usd=0.001
    ))
    
    # Mock parser
    from src.architect.schemas import RefactorPlan
    mock_plan = RefactorPlan(
        plan_id="test",
        description="Test refactor",
        files=[],
        primary_changes=[],
        dependencies=[],
        estimated_impact="low"
    )
    mock_reasoner.plan_parser.parse = Mock(return_value=(mock_plan, Mock(is_valid=True, errors=[], warnings=[])))
    mock_reasoner.plan_validator.validate_plan = Mock(return_value=Mock(is_valid=True, errors=[], warnings=[]))
    
    # Generate plan (without deep context)
    plan = mock_reasoner.generate_refactor_plan(
        task_description="Refactor auth",
        target_file="auth.ts",
        use_deep_context=False  # Use Phase 2 serializer
    )
    
    assert plan is not None
    assert plan.plan_id == "test"
    
    # Verify _retrieve_context was called with use_deep_context=False
    mock_retrieve.assert_called_once()
    call_kwargs = mock_retrieve.call_args[1]
    assert call_kwargs['use_deep_context'] == False


@patch.object(Reasoner, '_retrieve_context')
def test_generate_refactor_plan_with_deep_context(mock_retrieve, mock_reasoner):
    """Test deep context refactor plan generation (Phase 3 encoder)."""
    # Mock context retrieval with deep context
    mock_retrieve.return_value = [
        CompressedContextBlock(
            block_id="mock_2",
            block_type="file",
            content="# Compressed context from Jamba",
            format="markdown",
            token_count=500
        )
    ]
    
    # Mock LLM response
    mock_reasoner.llm_client.generate = Mock(return_value=Mock(
        content='{"plan_id": "test_deep", "files": [], "dependencies": [], "estimated_impact": "medium"}',
        output_tokens=100,
        cost_usd=0.002
    ))
    
    # Mock parser
    from src.architect.schemas import RefactorPlan
    mock_plan = RefactorPlan(
        plan_id="test_deep",
        description="Test deep refactor",
        files=[],
        primary_changes=[],
        dependencies=[],
        estimated_impact="medium"
    )
    mock_reasoner.plan_parser.parse = Mock(return_value=(mock_plan, Mock(is_valid=True, errors=[], warnings=[])))
    mock_reasoner.plan_validator.validate_plan = Mock(return_value=Mock(is_valid=True, errors=[], warnings=[]))
    
    # Generate plan (with deep context)
    plan = mock_reasoner.generate_refactor_plan(
        task_description="Refactor entire auth system",
        target_file="auth.ts",
        use_deep_context=True  # Use Phase 3 encoder
    )
    
    assert plan is not None
    assert plan.plan_id == "test_deep"
    
    # Verify _retrieve_context was called with use_deep_context=True
    mock_retrieve.assert_called_once()
    call_kwargs = mock_retrieve.call_args[1]
    assert call_kwargs['use_deep_context'] == True


@patch('src.reasoner.reasoner.GraphRetriever')
def test_retrieve_context_with_encoder(mock_retriever_class, mock_reasoner, mock_graph_context):
    """Test that _retrieve_context uses encoder when use_deep_context=True."""
    # Mock retriever
    mock_retriever = Mock()
    mock_retriever.get_file_context.return_value = mock_graph_context
    mock_reasoner.retriever = mock_retriever
    
    # Mock encoder
    from src.context_encoder.encoder import CompressedContext
    mock_compressed = CompressedContext(
        summary="# Technical Summary\nCompressed context",
        file_references=["src/auth/login.ts"],
        tokens_in=1000,
        tokens_out=200,
        compression_ratio=5.0,
        metadata={"model": "jamba"}
    )
    mock_reasoner.encoder.compress = Mock(return_value=mock_compressed)
    
    # Retrieve context with deep encoding
    blocks = mock_reasoner._retrieve_context(
        target_file="src/auth/login.ts",
        context_files=None,
        max_tokens=100_000,
        use_deep_context=True
    )
    
    # Verify encoder was called
    mock_reasoner.encoder.compress.assert_called_once()
    
    # Verify block was created
    assert len(blocks) == 1
    assert blocks[0].content == "# Technical Summary\nCompressed context"
    assert blocks[0].token_count == 200


@patch('src.reasoner.reasoner.GraphRetriever')
def test_retrieve_context_without_encoder(mock_retriever_class, mock_reasoner, mock_graph_context):
    """Test that _retrieve_context uses serializer when use_deep_context=False."""
    # Mock retriever
    mock_retriever = Mock()
    mock_retriever.get_file_context.return_value = mock_graph_context
    mock_reasoner.retriever = mock_retriever
    
    # Mock serializer
    mock_block = CompressedContextBlock(
        block_id="mock_3",
        block_type="file",
        content="# Markdown context",
        format="markdown",
        token_count=150
    )
    mock_reasoner.serializer.serialize_file_context = Mock(return_value=mock_block)
    
    # Retrieve context without deep encoding
    blocks = mock_reasoner._retrieve_context(
        target_file="src/auth/login.ts",
        context_files=None,
        max_tokens=100_000,
        use_deep_context=False
    )
    
    # Verify serializer was called
    mock_reasoner.serializer.serialize_file_context.assert_called_once()
    
    # Verify block was created
    assert len(blocks) == 1
    assert blocks[0].content == "# Markdown context"
    assert blocks[0].token_count == 150
