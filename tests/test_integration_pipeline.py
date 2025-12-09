"""
Integration tests for end-to-end Ouroboros pipeline.

Tests the complete workflow:
    Phase 1: Librarian → Phase 2: Reasoner → Phase 3: Jamba → Phase 4: Builder

Created: 2025-12-10
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from src.ouroboros_pipeline import (
    OuroborosCodeGenerator,
    GenerationRequest,
    GenerationResult,
)
from src.diffusion.builder import GeneratedPatch, RefactorPlan
from src.diffusion.config import MOCK_CONFIG


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace with sample code."""
    # Create directory structure
    src_dir = tmp_path / "src" / "services"
    src_dir.mkdir(parents=True)
    
    # Create sample Python file
    user_service = src_dir / "user_service.py"
    user_service.write_text("""
def get_user_by_id(user_id):
    # TODO: Add caching
    user = database.query('SELECT * FROM users WHERE id = ?', user_id)
    return user

def get_users_by_role(role):
    users = database.query('SELECT * FROM users WHERE role = ?', role)
    return users

class UserService:
    def __init__(self, db):
        self.db = db
    
    def create_user(self, username, email):
        return self.db.insert('users', {'username': username, 'email': email})
""")
    
    return tmp_path


@pytest.fixture
def mock_graph_db():
    """Mock graph database."""
    db = Mock()
    
    # Mock node data
    file_node = {
        "id": "file_1",
        "path": "src/services/user_service.py",
        "language": "python"
    }
    
    func_node = {
        "id": "func_1",
        "name": "get_user_by_id",
        "code": "def get_user_by_id(user_id):\n    user = database.query(...)\n    return user",
        "complexity": 5
    }
    
    # Configure mocks
    db.execute_query.return_value = []
    
    return db


@pytest.fixture
def mock_generator(temp_workspace, mock_graph_db):
    """Create generator with mocked components."""
    with patch('src.ouroboros_pipeline.OuroborosGraphDB') as MockGraphDB:
        MockGraphDB.return_value = mock_graph_db
        
        generator = OuroborosCodeGenerator(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            use_mock=True
        )
        
        yield generator
        
        generator.close()


def test_generator_initialization(mock_generator):
    """Test that generator initializes all components."""
    assert mock_generator.graph_db is not None
    assert mock_generator.retriever is not None
    assert mock_generator.dependency_analyzer is not None
    assert mock_generator.builder is not None
    assert mock_generator.diffusion_config == MOCK_CONFIG


def test_generation_request_creation():
    """Test GenerationRequest dataclass."""
    request = GenerationRequest(
        issue_description="Add caching",
        target_files=[Path("src/test.py")],
        target_functions=["func1"],
        context_limit=4096,
        priority=5
    )
    
    assert request.issue_description == "Add caching"
    assert len(request.target_files) == 1
    assert request.target_functions == ["func1"]
    assert request.context_limit == 4096
    assert request.priority == 5


def test_generation_result_applicable_patches():
    """Test filtering applicable patches."""
    # Create mock patches with different risk scores
    patches = []
    
    for i, (valid, risk) in enumerate([
        (True, 0.2),   # Low risk, valid
        (True, 0.5),   # Medium risk, valid
        (True, 0.8),   # High risk, valid
        (False, 0.3),  # Low risk, invalid
    ]):
        patch = Mock(spec=GeneratedPatch)
        patch.can_apply.return_value = valid
        patch.risk_score.return_value = risk
        patches.append(patch)
    
    result = GenerationResult(
        patches=patches,
        refactor_plans=[],
        compressed_contexts=[],
        success=True
    )
    
    # Test max_risk filtering
    applicable = result.get_applicable_patches(max_risk=0.5)
    assert len(applicable) == 2  # Only first two (valid + risk <= 0.5)
    
    # Test high-risk detection
    high_risk = result.get_high_risk_patches(threshold=0.5)
    assert len(high_risk) == 1  # Only the 0.8 risk patch


def test_determine_language(mock_generator):
    """Test language detection from file extension."""
    assert mock_generator._determine_language(Path("test.py")) == "python"
    assert mock_generator._determine_language(Path("test.ts")) == "typescript"
    assert mock_generator._determine_language(Path("test.js")) == "javascript"
    assert mock_generator._determine_language(Path("test.tsx")) == "typescript"
    assert mock_generator._determine_language(Path("test.jsx")) == "javascript"
    assert mock_generator._determine_language(Path("test.unknown")) == "python"  # default


def test_calculate_priority(mock_generator):
    """Test priority calculation."""
    # Test base priority
    func_node = {"complexity": 5}
    impact = {"impact_score": 0.5}
    priority = mock_generator._calculate_priority(func_node, impact, base_priority=5)
    assert priority == 5
    
    # Test high impact boost
    impact = {"impact_score": 0.8}
    priority = mock_generator._calculate_priority(func_node, impact, base_priority=5)
    assert priority == 7  # +2 for high impact
    
    # Test complexity reduction
    func_node = {"complexity": 25}
    impact = {"impact_score": 0.5}
    priority = mock_generator._calculate_priority(func_node, impact, base_priority=5)
    assert priority == 3  # -2 for high complexity
    
    # Test bounds
    func_node = {"complexity": 5}
    impact = {"impact_score": 1.0}
    priority = mock_generator._calculate_priority(func_node, impact, base_priority=10)
    assert priority == 10  # Capped at 10


def test_create_condition(mock_generator):
    """Test condition/prompt creation."""
    func_node = {"name": "get_user"}
    dependencies = [{"name": "database"}, {"name": "cache"}]
    impact = {"impact_score": 0.8}
    
    condition = mock_generator._create_condition(
        "Add caching",
        func_node,
        dependencies,
        impact
    )
    
    assert "Add caching" in condition
    assert "get_user" in condition
    assert "database" in condition
    assert "cache" in condition
    assert "High impact" in condition


def test_update_config(mock_generator):
    """Test config switching."""
    from src.diffusion.config import FAST_CONFIG, BALANCED_CONFIG, QUALITY_CONFIG
    
    # Test fast config
    mock_generator._update_config("fast")
    assert mock_generator.diffusion_config == FAST_CONFIG
    
    # Test balanced config
    mock_generator._update_config("balanced")
    assert mock_generator.diffusion_config == BALANCED_CONFIG
    
    # Test quality config
    mock_generator._update_config("quality")
    assert mock_generator.diffusion_config == QUALITY_CONFIG
    
    # Test mock config
    mock_generator._update_config("mock")
    assert mock_generator.diffusion_config == MOCK_CONFIG


def test_gather_context(mock_generator):
    """Test context gathering."""
    plan = RefactorPlan(
        file_path=Path("test.py"),
        edit_targets=["func1"],
        intent="Add caching",
        condition="Improve performance",
        context={
            "func_node_id": "func_1",
            "dependencies": [{"name": "dep1"}, {"name": "dep2"}]
        }
    )
    
    # Mock retriever
    mock_generator.retriever.get_node = Mock(return_value={
        "id": "func_1",
        "name": "func1",
        "code": "def func1():\n    pass"
    })
    
    context = mock_generator._gather_context(plan)
    
    assert "Add caching" in context
    assert "def func1" in context
    assert "dep1" in context
    assert "dep2" in context


def test_apply_patch_dry_run(mock_generator, temp_workspace):
    """Test patch application in dry-run mode."""
    # Create mock patch
    file_path = temp_workspace / "test.py"
    file_path.write_text("original code")
    
    patch = Mock(spec=GeneratedPatch)
    patch.can_apply.return_value = True
    patch.risk_score.return_value = 0.2
    patch.file_path = file_path
    patch.original_code = "original code"
    patch.generated_code = "new code"
    patch.unified_diff = "--- test.py\n+++ test.py\n-original\n+new"
    
    # Dry run should not modify file
    success = mock_generator.apply_patch(patch, dry_run=True)
    
    assert success is True
    assert file_path.read_text() == "original code"  # Unchanged


def test_apply_patch_real(mock_generator, temp_workspace):
    """Test actual patch application."""
    file_path = temp_workspace / "test.py"
    file_path.write_text("original code")
    
    patch = Mock(spec=GeneratedPatch)
    patch.can_apply.return_value = True
    patch.risk_score.return_value = 0.2
    patch.file_path = file_path
    patch.original_code = "original code"
    patch.generated_code = "new code"
    patch.unified_diff = "--- test.py\n+++ test.py\n-original\n+new"
    
    # Real application
    success = mock_generator.apply_patch(patch, backup=True)
    
    assert success is True
    assert file_path.read_text() == "new code"
    
    # Check backup was created
    backup_path = Path(str(file_path) + ".backup")
    assert backup_path.exists()
    assert backup_path.read_text() == "original code"


def test_apply_patch_invalid(mock_generator):
    """Test that invalid patches are rejected."""
    patch = Mock(spec=GeneratedPatch)
    patch.can_apply.return_value = False
    
    success = mock_generator.apply_patch(patch)
    
    assert success is False


def test_context_manager(temp_workspace):
    """Test generator as context manager."""
    # In mock mode, the generator creates its own mocks internally
    with OuroborosCodeGenerator(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        use_mock=True,
        skip_db_init=True,  # Skip DB init in test mode
    ) as generator:
        assert generator is not None
        assert generator.graph_db is not None
        
        # Store the mock for later verification
        graph_db_mock = generator.graph_db
    
    # Check close was called
    graph_db_mock.close.assert_called_once()


def test_generate_no_target_files(mock_generator):
    """Test generation without target files."""
    result = mock_generator.generate(
        issue_description="Optimize performance",
        config="mock"
    )
    
    # Should still return a result (empty plans)
    assert isinstance(result, GenerationResult)
    assert result.success is False  # No plans generated
    assert "No refactor plans" in result.errors[0]


def test_generate_with_max_patches(mock_generator):
    """Test patch limit enforcement."""
    # Mock retriever to return multiple functions
    mock_generator.retriever.get_nodes_by_property = Mock(return_value=[
        {"id": "file_1", "path": "test.py"}
    ])
    
    mock_generator.retriever.get_related_nodes = Mock(return_value=[
        {"id": f"func_{i}", "name": f"func{i}", "complexity": 5}
        for i in range(20)  # 20 functions
    ])
    
    mock_generator.dependency_analyzer.get_dependencies = Mock(return_value=[])
    
    # Generate with max_patches=5
    result = mock_generator.generate(
        issue_description="Refactor functions",
        target_files=["test.py"],
        max_patches=5,
        config="mock"
    )
    
    # Should limit to 5 patches
    assert len(result.patches) <= 5


def test_compress_contexts_mock_mode(mock_generator):
    """Test that context compression is skipped in mock mode."""
    plans = [
        RefactorPlan(
            file_path=Path("test.py"),
            edit_targets=["func1"],
            intent="Test",
            condition="Test condition",
            language="python"
        )
    ]
    
    contexts = mock_generator._compress_contexts(plans, context_limit=4096)
    
    # Should return empty in mock mode
    assert len(contexts) == 0


def test_generation_error_handling(mock_generator):
    """Test that errors are caught and returned in result."""
    # Make retriever raise an error
    mock_generator.retriever.get_nodes_by_property = Mock(
        side_effect=Exception("Database error")
    )
    
    result = mock_generator.generate(
        issue_description="Test",
        target_files=["test.py"],
        config="mock"
    )
    
    assert result.success is False
    assert len(result.errors) > 0
    assert "Database error" in result.errors[0]


def test_generation_metadata(mock_generator):
    """Test that generation metadata is populated."""
    result = mock_generator.generate(
        issue_description="Test",
        target_files=["nonexistent.py"],
        config="mock"
    )
    
    assert "duration_seconds" in result.metadata
    assert "timestamp" in result.metadata
    assert result.metadata["duration_seconds"] >= 0


@pytest.mark.integration
def test_end_to_end_generation_mock(mock_generator, temp_workspace):
    """
    Integration test: Full generation pipeline with mock mode.
    
    This tests the complete workflow without real API calls or database.
    """
    # Create test file
    test_file = temp_workspace / "src" / "services" / "user_service.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("""
def get_user_by_id(user_id):
    return database.query('SELECT * FROM users WHERE id = ?', user_id)

def get_users_by_role(role):
    return database.query('SELECT * FROM users WHERE role = ?', role)
""")
    
    # Mock retriever responses
    mock_generator.retriever.get_nodes_by_property = Mock(return_value=[
        {"id": "file_1", "path": str(test_file)}
    ])
    
    mock_generator.retriever.get_related_nodes = Mock(return_value=[
        {"id": "func_1", "name": "get_user_by_id", "complexity": 5,
         "code": "def get_user_by_id(user_id):\n    return database.query(...)"}
    ])
    
    mock_generator.dependency_analyzer.get_dependencies = Mock(return_value=[
        {"name": "database", "type": "module"}
    ])
    
    # Simple impact (no impact_analyzer)
    impact = {"impact_score": 0.6, "num_dependencies": 1}
    
    # Generate
    result = mock_generator.generate(
        issue_description="Add caching to database queries",
        target_files=[str(test_file)],
        config="mock"
    )
    
    # Verify result
    assert result.success is True
    assert len(result.patches) > 0
    
    # Check first patch
    patch = result.patches[0]
    assert patch.file_path == test_file
    assert patch.is_valid_syntax is not None
    
    # Try to apply (dry run)
    success = mock_generator.apply_patch(patch, dry_run=True)
    assert success is True or not patch.can_apply()


def test_generation_with_specific_functions(mock_generator):
    """Test generation targeting specific functions."""
    # Mock retriever
    mock_generator.retriever.get_nodes_by_property = Mock(return_value=[
        {"id": "file_1", "path": "test.py"}
    ])
    
    mock_generator.retriever.get_related_nodes = Mock(return_value=[
        {"id": "func_1", "name": "target_func", "complexity": 5},
        {"id": "func_2", "name": "other_func", "complexity": 5},
    ])
    
    mock_generator.dependency_analyzer.get_dependencies = Mock(return_value=[])
    
    # Generate targeting only "target_func"
    result = mock_generator.generate(
        issue_description="Refactor",
        target_files=["test.py"],
        target_functions=["target_func"],
        config="mock"
    )
    
    # Should only generate for target_func
    if result.success and result.refactor_plans:
        for plan in result.refactor_plans:
            assert "target_func" in plan.edit_targets
