"""
Tests for Phase 3: Context Encoder
===================================

Tests the Jamba-based context compression system.
"""

import pytest
from src.context_encoder import (
    ContextEncoder,
    ContextEncoderConfig,
    EncoderProvider,
    JambaConfig,
)
from src.context_encoder.validator import ValidationResult


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = ContextEncoderConfig()
    config.provider = EncoderProvider.MOCK
    return config


@pytest.fixture
def encoder(mock_config):
    """Create a context encoder with mock provider."""
    return ContextEncoder(mock_config)


@pytest.fixture
def sample_codebase():
    """Sample codebase context for testing."""
    return """
# File: src/auth/login.ts
import { User } from '../models/user';
import { Firebase } from '../lib/firebase';

export class LoginService {
    async loginWithFirebase(email: string, password: string): Promise<User> {
        const firebase = new Firebase();
        return await firebase.auth(email, password);
    }
}

# File: src/models/user.ts
export interface User {
    id: string;
    email: string;
    name: string;
}

# File: src/lib/firebase.ts
export class Firebase {
    async auth(email: string, password: string): Promise<any> {
        // Firebase authentication logic
    }
}
"""


def test_context_encoder_initialization(mock_config):
    """Test that context encoder initializes correctly."""
    encoder = ContextEncoder(mock_config)
    assert encoder.config.provider == EncoderProvider.MOCK
    assert encoder.validator is not None


def test_jamba_config_validation():
    """Test Jamba configuration validation."""
    # Valid config
    config = JambaConfig()
    assert config.context_window == 256_000
    assert config.max_output_tokens <= config.context_window
    
    # Invalid config should raise error
    with pytest.raises(ValueError):
        invalid_config = JambaConfig(
            context_window=10_000,
            max_output_tokens=20_000  # Exceeds context window
        )


def test_context_compression_mock(encoder, sample_codebase):
    """Test context compression with mock provider."""
    target_files = ["src/auth/login.ts", "src/models/user.ts"]
    
    compressed = encoder.compress(
        codebase_context=sample_codebase,
        target_files=target_files,
        metadata={"prompt_id": "test_001"},
    )
    
    # Check compressed context properties
    assert compressed.summary is not None
    assert len(compressed.summary) > 0
    assert compressed.file_references == target_files
    assert compressed.tokens_in > 0
    assert compressed.tokens_out > 0
    assert compressed.compression_ratio > 0
    
    # Check metadata
    assert compressed.metadata["model"] == encoder.config.model_version
    assert compressed.metadata["provider"] == "mock"
    assert compressed.metadata["prompt_id"] == "test_001"
    
    # Check checksum
    checksum = compressed.checksum()
    assert len(checksum) == 64  # SHA-256 hex digest


def test_context_validation_pass(encoder, sample_codebase):
    """Test that valid context passes validation."""
    compressed = encoder.compress(
        codebase_context=sample_codebase,
        target_files=["src/auth/login.ts"],
    )
    
    # Should not raise error (validation passed internally)
    assert compressed is not None
    assert len(compressed.summary) > 0


def test_context_validation_empty_summary(encoder):
    """Test validation fails for empty summary."""
    from src.context_encoder.encoder import CompressedContext
    
    # Create invalid compressed context
    invalid_context = CompressedContext(
        summary="",  # Empty summary
        file_references=["test.ts"],
        tokens_in=100,
        tokens_out=0,
        compression_ratio=0,
        metadata={},
    )
    
    result = encoder.validator.validate(invalid_context, "original context")
    
    assert not result.is_valid
    assert len(result.errors) > 0
    assert any("empty" in error.lower() for error in result.errors)


def test_context_validation_missing_file_refs(encoder, sample_codebase):
    """Test validation detects missing file references."""
    from src.context_encoder.encoder import CompressedContext
    
    # Create context that doesn't reference target files
    context = CompressedContext(
        summary="Generic summary without specific file names",
        file_references=["src/auth/login.ts", "src/models/user.ts"],
        tokens_in=100,
        tokens_out=50,
        compression_ratio=2.0,
        metadata={},
    )
    
    result = encoder.validator.validate(context, sample_codebase)
    
    # Should have errors about missing file references
    assert len(result.errors) > 0


def test_hallucination_detection(encoder):
    """Test hallucination detection in summaries."""
    original = "User class with login method"
    
    # Valid summary (no hallucination)
    summary_valid = "The User class contains a login method for authentication"
    score_valid = encoder.validator._detect_hallucinations(summary_valid, original)
    assert score_valid < 0.5  # Low hallucination
    
    # Hallucinated summary
    summary_invalid = "The DatabasePool class manages MongoDB connections with Redis caching"
    score_invalid = encoder.validator._detect_hallucinations(summary_invalid, original)
    assert score_invalid > score_valid  # Higher hallucination


def test_compression_ratio_calculation(encoder, sample_codebase):
    """Test that compression ratio is calculated correctly."""
    compressed = encoder.compress(
        codebase_context=sample_codebase,
        target_files=["src/auth/login.ts"],
    )
    
    # Compression ratio should be > 1 (input > output)
    assert compressed.compression_ratio > 1.0
    assert compressed.compression_ratio == compressed.tokens_in / compressed.tokens_out


def test_context_serialization(encoder, sample_codebase):
    """Test that compressed context can be serialized."""
    compressed = encoder.compress(
        codebase_context=sample_codebase,
        target_files=["src/auth/login.ts"],
    )
    
    # Convert to dict
    data = compressed.to_dict()
    
    assert isinstance(data, dict)
    assert "summary" in data
    assert "file_references" in data
    assert "tokens_in" in data
    assert "tokens_out" in data
    assert "compression_ratio" in data
    assert "timestamp" in data
    assert "metadata" in data


def test_structural_completeness_check(encoder):
    """Test structural completeness validation."""
    # Complete summary
    summary_complete = """
    # File: test.ts
    class User {
        function login() {}
    }
    import { Firebase } from './lib';
    """
    warnings_complete = encoder.validator._check_structural_completeness(summary_complete)
    assert len(warnings_complete) == 0  # No warnings
    
    # Incomplete summary (missing imports)
    summary_incomplete = """
    class User {
        function login() {}
    }
    """
    warnings_incomplete = encoder.validator._check_structural_completeness(summary_incomplete)
    assert len(warnings_incomplete) > 0  # Should have warnings


@pytest.mark.skipif(
    True,  # Skip by default - requires AI21 Cloud or LM Studio running
    reason="Requires Jamba (AI21 Cloud API key or LM Studio)"
)
def test_jamba_integration_cloud():
    """Integration test with real Jamba model via AI21 Cloud."""
    import os
    
    # Skip if no API key
    if not os.getenv("AI21_API_KEY"):
        pytest.skip("AI21_API_KEY not set")
    
    from src.context_encoder.config import JambaConfig, EncoderProvider
    
    config = ContextEncoderConfig()
    config.provider = EncoderProvider.JAMBA_CLOUD
    config.jamba = JambaConfig(use_cloud=True)
    
    encoder = ContextEncoder(config)
    
    sample_code = """
    export class AuthService {
        login(email: string, password: string) {
            // Auth logic
        }
    }
    """
    
    compressed = encoder.compress(
        codebase_context=sample_code,
        target_files=["auth.ts"],
    )
    
    assert compressed.summary is not None
    assert "AuthService" in compressed.summary or "auth" in compressed.summary.lower()
    assert compressed.compression_ratio > 0


@pytest.mark.skipif(
    True,  # Skip by default - requires LM Studio running
    reason="Requires Jamba-1.5-Mini running in LM Studio"
)
def test_jamba_integration_local():
    """Integration test with Jamba via LM Studio local."""
    from src.context_encoder.config import JambaConfig, EncoderProvider
    
    config = ContextEncoderConfig()
    config.provider = EncoderProvider.JAMBA_LOCAL
    config.jamba = JambaConfig(use_cloud=False)
    
    encoder = ContextEncoder(config)
    
    sample_code = """
    export class AuthService {
        login(email: string, password: string) {
            // Auth logic
        }
    }
    """
    
    compressed = encoder.compress(
        codebase_context=sample_code,
        target_files=["auth.ts"],
    )
    
    assert compressed.summary is not None
    assert "AuthService" in compressed.summary or "auth" in compressed.summary.lower()
