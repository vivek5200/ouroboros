"""
Tests for Discrete Diffusion Model
====================================

Tests the discrete diffusion engine for code generation.
"""

import pytest
import numpy as np
from src.diffusion import (
    DiscreteDiffusionModel,
    DiffusionConfig,
    DiffusionBackbone,
    NoiseSchedule,
    NoiseScheduler,
    ASTMasker,
    MaskingStrategy,
    MOCK_CONFIG,
    FAST_CONFIG,
)


# Test code samples
PYTHON_CODE = '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n-1)
'''


@pytest.fixture
def mock_model():
    """Create mock diffusion model for testing."""
    return DiscreteDiffusionModel(MOCK_CONFIG)


@pytest.fixture
def masked_code_sample():
    """Create masked code sample."""
    masker = ASTMasker(language="python")
    masked, spans = masker.mask(
        PYTHON_CODE,
        strategy=MaskingStrategy.FUNCTION_BODY,
        mask_ratio=0.5
    )
    return masked, spans


def test_noise_scheduler_linear():
    """Test linear noise schedule."""
    scheduler = NoiseScheduler(
        num_steps=1000,
        schedule=NoiseSchedule.LINEAR,
        beta_start=0.0001,
        beta_end=0.02
    )
    
    assert len(scheduler.betas) == 1000
    assert scheduler.betas[0] == pytest.approx(0.0001, rel=1e-4)
    assert scheduler.betas[-1] == pytest.approx(0.02, rel=1e-4)
    
    # Check monotonic increase
    assert all(scheduler.betas[i] <= scheduler.betas[i+1] for i in range(len(scheduler.betas)-1))


def test_noise_scheduler_cosine():
    """Test cosine noise schedule."""
    scheduler = NoiseScheduler(
        num_steps=1000,
        schedule=NoiseSchedule.COSINE
    )
    
    assert len(scheduler.betas) == 1000
    # Cosine schedule should have valid betas (between 0 and 1)
    assert all(0 <= b <= 0.999 for b in scheduler.betas)
    # Alphas should be positive
    assert all(a > 0 for a in scheduler.alphas)


def test_noise_scheduler_sqrt():
    """Test sqrt noise schedule."""
    scheduler = NoiseScheduler(
        num_steps=1000,
        schedule=NoiseSchedule.SQRT,
        beta_start=0.0001,
        beta_end=0.02
    )
    
    assert len(scheduler.betas) == 1000
    # Sqrt schedule should be between linear bounds
    assert scheduler.betas[0] >= 0.0001
    assert scheduler.betas[-1] <= 0.02


def test_diffusion_config_validation():
    """Test configuration validation."""
    # Valid config
    config = DiffusionConfig(mask_ratio=0.5, cfg_guidance_scale=7.5)
    config.validate()  # Should not raise
    
    # Invalid mask_ratio
    with pytest.raises(AssertionError):
        bad_config = DiffusionConfig(mask_ratio=0.0)
        bad_config.validate()
    
    # Invalid CFG scale
    with pytest.raises(AssertionError):
        bad_config = DiffusionConfig(cfg_guidance_scale=0.5)
        bad_config.validate()
    
    # Invalid sampling steps
    with pytest.raises(AssertionError):
        bad_config = DiffusionConfig(
            num_diffusion_steps=100,
            num_sampling_steps=200  # Can't be more than total steps
        )
        bad_config.validate()


def test_model_initialization(mock_model):
    """Test diffusion model initializes correctly."""
    assert mock_model.config.backbone == DiffusionBackbone.MOCK
    assert mock_model.scheduler is not None
    assert mock_model.masker is not None
    
    # Check scheduler is initialized
    assert mock_model.scheduler.num_steps == MOCK_CONFIG.num_diffusion_steps


def test_forward_diffusion(mock_model, masked_code_sample):
    """Test forward diffusion adds noise."""
    _, spans = masked_code_sample
    
    noisy_tokens = mock_model._forward_diffusion(spans)
    
    assert len(noisy_tokens) == len(spans)
    # Each span should have noisy tokens
    for noise in noisy_tokens:
        assert isinstance(noise, np.ndarray)
        assert len(noise) > 0


def test_generate_basic(mock_model, masked_code_sample):
    """Test basic code generation."""
    masked_code, spans = masked_code_sample
    
    sample = mock_model.generate(
        masked_code=masked_code,
        masked_spans=spans,
        condition="Implement fibonacci and factorial functions",
        language="python"
    )
    
    assert sample.generated_code is not None
    assert len(sample.generated_code) > 0
    assert sample.num_steps == MOCK_CONFIG.num_sampling_steps
    assert sample.cfg_scale == MOCK_CONFIG.cfg_guidance_scale
    assert isinstance(sample.is_valid_syntax, bool)
    assert isinstance(sample.generation_time_ms, float)
    assert sample.generation_time_ms >= 0  # Can be 0 for very fast mock generation


def test_generate_with_condition(mock_model):
    """Test generation with conditioning context."""
    code = "def foo():\n    [MASK]"
    masker = ASTMasker(language="python")
    
    # Manually create a span
    from src.diffusion.masking import MaskedSpan
    span = MaskedSpan(
        start_byte=15,
        end_byte=21,
        start_line=1,
        end_line=1,
        start_col=4,
        end_col=10,
        node_type="block",
        original_text="pass",
    )
    
    sample = mock_model.generate(
        masked_code=code,
        masked_spans=[span],
        condition="This function should return 42",
        language="python"
    )
    
    assert "[MASK]" not in sample.generated_code
    # Mock model should have replaced mask
    assert len(sample.generated_code) > len(code) - 6  # Roughly replaced [MASK]


def test_validation_errors(mock_model):
    """Test that validation errors are captured."""
    # Create intentionally invalid code structure
    invalid_code = "def foo(\n    [MASK]"
    from src.diffusion.masking import MaskedSpan
    
    span = MaskedSpan(
        start_byte=12,
        end_byte=18,
        start_line=1,
        end_line=1,
        start_col=12,
        end_col=18,
        node_type="block",
        original_text="invalid",
    )
    
    sample = mock_model.generate(
        masked_code=invalid_code,
        masked_spans=[span],
        language="python"
    )
    
    # Generated code might be invalid
    if not sample.is_valid_syntax:
        assert len(sample.validation_errors) > 0


def test_generate_with_fallback(mock_model, masked_code_sample):
    """Test generation with autoregressive fallback."""
    masked_code, spans = masked_code_sample
    
    sample = mock_model.generate_with_fallback(
        masked_code=masked_code,
        masked_spans=spans,
        condition="Test fallback",
        language="python",
        fallback_model="qwen2.5-coder-1.5b"
    )
    
    assert sample.generated_code is not None
    # Either diffusion succeeded or fallback was used
    assert "backbone" in sample.metadata or "fallback_model" in sample.metadata


def test_mock_predict_different_node_types(mock_model):
    """Test mock predictions for different AST node types."""
    from src.diffusion.masking import MaskedSpan
    
    # Function definition
    func_span = MaskedSpan(
        start_byte=0, end_byte=10,
        start_line=0, end_line=0,
        start_col=0, end_col=10,
        node_type="function_definition",
        original_text="def foo():"
    )
    pred = mock_model._mock_predict(func_span, None)
    assert "def" in pred and ":" in pred
    
    # Expression
    expr_span = MaskedSpan(
        start_byte=0, end_byte=10,
        start_line=0, end_line=0,
        start_col=0, end_col=10,
        node_type="expression_statement",
        original_text="x = 1"
    )
    pred = mock_model._mock_predict(expr_span, None)
    assert "=" in pred or "result" in pred
    
    # Identifier
    id_span = MaskedSpan(
        start_byte=0, end_byte=3,
        start_line=0, end_line=0,
        start_col=0, end_col=3,
        node_type="identifier",
        original_text="foo"
    )
    pred = mock_model._mock_predict(id_span, None)
    assert len(pred) > 0


def test_diffusion_sample_metadata(mock_model, masked_code_sample):
    """Test that DiffusionSample includes all required metadata."""
    masked_code, spans = masked_code_sample
    
    sample = mock_model.generate(
        masked_code=masked_code,
        masked_spans=spans,
        condition="Test metadata",
        language="python"
    )
    
    # Check metadata fields
    assert "language" in sample.metadata
    assert sample.metadata["language"] == "python"
    assert "backbone" in sample.metadata
    assert sample.metadata["backbone"] == "mock"
    assert "num_masked_spans" in sample.metadata
    assert sample.metadata["num_masked_spans"] == len(spans)
    assert "timestamp" in sample.metadata


def test_config_presets():
    """Test configuration presets."""
    from src.diffusion import get_config, FAST_CONFIG, BALANCED_CONFIG, QUALITY_CONFIG
    
    fast = get_config("fast")
    assert fast.backbone == DiffusionBackbone.QWEN25_CODER_15B
    assert fast.num_sampling_steps == 20
    
    balanced = get_config("balanced")
    assert balanced.backbone == DiffusionBackbone.QWEN25_CODER_7B
    assert balanced.num_sampling_steps == 50
    
    quality = get_config("quality")
    assert balanced.backbone == DiffusionBackbone.QWEN25_CODER_7B
    assert quality.num_sampling_steps == 100
    
    mock = get_config("mock")
    assert mock.backbone == DiffusionBackbone.MOCK


def test_diffusion_with_typescript(mock_model):
    """Test diffusion with TypeScript code."""
    ts_code = """
class User {
    constructor(public name: string) {}
    greet(): string {
        return `Hello, ${this.name}`;
    }
}
"""
    
    masker = ASTMasker(language="typescript")
    masked, spans = masker.mask(
        ts_code,
        strategy=MaskingStrategy.FUNCTION_BODY,
        mask_ratio=0.5
    )
    
    sample = mock_model.generate(
        masked_code=masked,
        masked_spans=spans,
        condition="TypeScript user class",
        language="typescript"
    )
    
    assert sample.generated_code is not None
    assert sample.metadata["language"] == "typescript"


def test_scheduler_get_methods():
    """Test NoiseScheduler getter methods."""
    scheduler = NoiseScheduler(num_steps=100, schedule=NoiseSchedule.LINEAR)
    
    beta_50 = scheduler.get_beta(50)
    assert isinstance(beta_50, (float, np.floating))
    
    alpha_50 = scheduler.get_alpha_cumprod(50)
    assert isinstance(alpha_50, (float, np.floating))
    assert 0 < alpha_50 < 1


def test_config_from_env(monkeypatch):
    """Test loading configuration from environment."""
    monkeypatch.setenv("DIFFUSION_BACKBONE", "qwen2.5-coder-7b")
    monkeypatch.setenv("DIFFUSION_STEPS", "500")
    monkeypatch.setenv("SAMPLING_STEPS", "25")
    monkeypatch.setenv("CFG_SCALE", "5.0")
    
    config = DiffusionConfig.from_env()
    
    assert config.backbone == DiffusionBackbone.QWEN25_CODER_7B
    assert config.num_diffusion_steps == 500
    assert config.num_sampling_steps == 25
    assert config.cfg_guidance_scale == 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
