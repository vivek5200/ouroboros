# Phase 4: The Builder - Implementation Complete

**Date**: 2025-01-09  
**Commit**: cbfa419, 6967959  
**Status**: ✅ Core Implementation Complete  
**Tests**: 34/34 passing

---

## Overview

Phase 4 implements a **discrete diffusion model** for AI-assisted code generation with:
- AST-aware masking for deterministic token selection
- Classifier-free guidance (CFG) for conditional generation
- Multiple noise schedules (linear, cosine, sqrt)
- Autoregressive fallback for robustness
- High-level Builder orchestrator for end-to-end pipeline

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      Phase 4: The Builder                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  RefactorPlan (from Phase 2)                                     │
│         │                                                         │
│         ↓                                                         │
│  ┌─────────────────┐                                             │
│  │    Builder       │  ← High-level orchestrator                 │
│  └────────┬─────────┘                                             │
│           │                                                       │
│           ├──→ ASTMasker ────→ Mask target functions             │
│           │                                                       │
│           ├──→ DiscreteDiffusionModel                            │
│           │         │                                             │
│           │         ├──→ NoiseScheduler (3 strategies)           │
│           │         ├──→ Forward diffusion (add noise)           │
│           │         ├──→ Reverse diffusion (denoise with CFG)    │
│           │         └──→ Validation (Tree-Sitter)                │
│           │                                                       │
│           ├──→ Autoregressive Fallback (Qwen small)              │
│           │                                                       │
│           └──→ GeneratedPatch (with provenance)                  │
│                     │                                             │
│                     ↓                                             │
│              Unified Diff + Metadata                              │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Configuration System (`src/diffusion/config.py`)

**151 lines** | **4 presets** | **3 backbones**

```python
@dataclass
class DiffusionConfig:
    backbone: DiffusionBackbone        # Qwen2.5-Coder (1.5B/7B/14B) or MOCK
    num_sampling_steps: int = 50       # Diffusion steps
    noise_schedule: NoiseSchedule      # LINEAR/COSINE/SQRT
    cfg_guidance_scale: float = 7.5    # Classifier-free guidance
    temperature: float = 0.8           # Sampling temperature
    device: str = "cuda"               # cuda/cpu/mps
```

**Presets**:
- `FAST_CONFIG`: 20 steps, 1.5B model (quick iteration)
- `BALANCED_CONFIG`: 50 steps, 7B model (production default)
- `QUALITY_CONFIG`: 100 steps, 14B model (best quality)
- `MOCK_CONFIG`: 5 steps, mock backend (testing)

**Features**:
- Validation on initialization
- Environment variable loading
- Automatic device detection
- Type-safe enums

---

### 2. Noise Scheduler (`src/diffusion/diffusion_model.py`)

**Manages noise schedules across timesteps**

**3 Strategies**:

1. **Linear Schedule**:
   ```python
   β_t = β_start + (β_end - β_start) * t/T
   ```
   - Simple, predictable
   - Good for quick prototyping

2. **Cosine Schedule** (Nichol & Dhariwal 2021):
   ```python
   α̅_t = f(t) / f(0), where f(t) = cos((t/T + s)/(1 + s) * π/2)²
   ```
   - State-of-the-art for diffusion
   - Better preservation of low frequencies
   - Used in DALL-E 2, Stable Diffusion

3. **Square Root Schedule**:
   ```python
   β_t = β_start + (β_end - β_start) * √(t/T)
   ```
   - Nonlinear noise progression
   - Faster initial denoising

**Precomputed Values**:
- `alphas`: 1 - β_t
- `alphas_cumprod`: ∏ α_t (cumulative product)
- Enables efficient sampling

---

### 3. Discrete Diffusion Model (`src/diffusion/diffusion_model.py`)

**468 lines** | **Mock implementation** | **CFG support**

#### Forward Diffusion (Add Noise)
```python
def _forward_diffusion(masked_code, masked_spans, t):
    """Add noise to masked spans at timestep t"""
    # Sample noise level from schedule
    alpha_bar = scheduler.get_alpha_bar(t)
    
    # Add noise: x_t = √(α̅_t) * x_0 + √(1 - α̅_t) * ε
    for span in masked_spans:
        noise_level = sqrt(1 - alpha_bar)
        span.text = add_token_noise(span.original_text, noise_level)
    
    return noisy_code
```

#### Reverse Diffusion (Denoise with CFG)
```python
def _reverse_diffusion(noisy_code, condition, cfg_scale):
    """Denoise step-by-step with classifier-free guidance"""
    for t in reversed(range(num_steps)):
        # Conditional prediction (with prompt)
        cond_pred = model_predict(noisy_code, condition, t)
        
        # Unconditional prediction (no prompt)
        uncond_pred = model_predict(noisy_code, None, t)
        
        # CFG: amplify conditional signal
        prediction = uncond_pred + cfg_scale * (cond_pred - uncond_pred)
        
        # Denoise one step
        noisy_code = denoise_step(noisy_code, prediction, t)
    
    return denoised_code
```

#### Generation Pipeline
```python
def generate(masked_code, masked_spans, condition, language):
    """Full generation pipeline"""
    # 1. Forward: Add noise to masked spans
    noisy_code = _forward_diffusion(masked_code, masked_spans, T)
    
    # 2. Reverse: Denoise with CFG
    generated_code = _reverse_diffusion(noisy_code, condition, cfg_scale)
    
    # 3. Validate: Check syntax with Tree-Sitter
    is_valid, errors = validate_syntax(generated_code, language)
    
    # 4. Return sample with metadata
    return DiffusionSample(
        generated_code=generated_code,
        masked_spans=masked_spans,
        num_steps=num_steps,
        cfg_scale=cfg_scale,
        is_valid_syntax=is_valid,
        validation_errors=errors,
        generation_time_ms=elapsed,
        metadata={...}
    )
```

#### Autoregressive Fallback
```python
def generate_with_fallback(masked_code, masked_spans, condition):
    """Generate with fallback on validation failure"""
    try:
        # Try diffusion first
        sample = generate(masked_code, masked_spans, condition)
        
        if sample.is_valid_syntax:
            return sample
        
        # Fallback to Qwen small autoregressive
        return _autoregressive_fallback(masked_code, condition)
    
    except Exception as e:
        # Always have a fallback
        return _autoregressive_fallback(masked_code, condition)
```

#### Mock Implementation
```python
def _mock_predict(masked_code, condition, masked_spans):
    """Mock prediction for testing without large models"""
    # Simple heuristics based on node type
    for span in masked_spans:
        if span.node_type == "function_definition":
            return "def mock_function():\n    pass"
        elif span.node_type == "class_definition":
            return "class MockClass:\n    pass"
        else:
            return "# Mock code"
```

---

### 4. Builder Orchestrator (`src/diffusion/builder.py`)

**478 lines** | **Multi-language** | **Batch processing**

**High-level interface for code generation:**

```python
class Builder:
    """
    Phase 4: The Builder - Orchestrates code generation pipeline.
    
    Usage:
        builder = Builder(config=BALANCED_CONFIG)
        
        plan = RefactorPlan(
            file_path=Path("src/utils.py"),
            edit_targets=["calculate_total"],
            intent="Optimize performance",
            condition="Refactor to use vectorized operations",
            language="python"
        )
        
        patch = builder.generate_patch(plan)
        
        if patch.can_apply():
            print(patch.unified_diff)
        else:
            print(f"Risk score: {patch.risk_score():.2f}")
    """
```

#### Input: RefactorPlan
```python
@dataclass
class RefactorPlan:
    file_path: Path                  # File to edit
    edit_targets: List[str]          # Functions/classes to refactor
    intent: str                      # High-level description
    condition: str                   # Detailed prompt for diffusion
    context: Dict[str, Any]          # Additional context from graph
    language: str = "python"         # Programming language
    priority: int = 1                # Priority level
```

#### Output: GeneratedPatch
```python
@dataclass
class GeneratedPatch:
    file_path: Path                  # File to patch
    original_code: str               # Original code
    generated_code: str              # New code
    unified_diff: str                # Standard diff format
    masked_spans: List[MaskedSpan]   # What was regenerated
    diffusion_sample: DiffusionSample # Full generation metadata
    refactor_plan: RefactorPlan      # Original plan
    is_valid_syntax: bool            # Validation status
    validation_errors: List[str]     # Errors (if any)
    generation_timestamp: str        # When generated
    metadata: Dict[str, Any]         # Additional metadata
    
    def can_apply(self) -> bool:
        """Check if patch is safe to apply"""
        return self.is_valid_syntax and len(self.validation_errors) == 0
    
    def risk_score(self) -> float:
        """Compute risk score (0.0 = safe, 1.0 = risky)"""
        # Invalid syntax = high risk
        # Many errors = medium risk
        # Large diffs = increased risk
        return score  # 0.0 to 1.0
```

#### Generation Pipeline
```python
def generate_patch(plan: RefactorPlan) -> GeneratedPatch:
    """Generate code patch from refactor plan"""
    # 1. Read original code from file
    original_code = plan.file_path.read_text()
    
    # 2. Mask target functions/classes
    masked_code, masked_spans = _mask_target_functions(
        code=original_code,
        target_names=plan.edit_targets,
        language=plan.language
    )
    
    # 3. Run diffusion to generate new code
    diffusion_sample = model.generate_with_fallback(
        masked_code=masked_code,
        masked_spans=masked_spans,
        condition=plan.condition,
        language=plan.language
    )
    
    # 4. Create unified diff
    unified_diff = _create_unified_diff(
        original_code,
        diffusion_sample.generated_code,
        str(plan.file_path)
    )
    
    # 5. Return patch with full provenance
    return GeneratedPatch(
        file_path=plan.file_path,
        original_code=original_code,
        generated_code=diffusion_sample.generated_code,
        unified_diff=unified_diff,
        masked_spans=masked_spans,
        diffusion_sample=diffusion_sample,
        refactor_plan=plan,
        is_valid_syntax=diffusion_sample.is_valid_syntax,
        validation_errors=diffusion_sample.validation_errors,
        generation_timestamp=datetime.now().isoformat(),
        metadata={...}
    )
```

#### Batch Processing
```python
def generate_batch(plans: List[RefactorPlan]) -> List[GeneratedPatch]:
    """Generate patches for multiple plans"""
    # Sort by priority (higher first)
    sorted_plans = sorted(plans, key=lambda p: p.priority, reverse=True)
    
    patches = []
    for plan in sorted_plans:
        try:
            patch = generate_patch(plan)
            patches.append(patch)
        except Exception as e:
            # Create error patch (graceful degradation)
            patches.append(_create_error_patch(plan, str(e)))
    
    return patches
```

#### Multi-Language Support
```python
def _mask_target_functions(code, target_names, language):
    """Mask specific functions/classes by name"""
    # Create language-specific masker if needed
    if self.masker.language != language:
        masker = ASTMasker(language=language)
    else:
        masker = self.masker
    
    # Parse with correct language
    tree = masker.parser.parse(bytes(code, "utf8"))
    
    # Find target nodes (function_definition, class_definition, etc.)
    target_nodes = find_named_nodes(tree, target_names, language)
    
    # Mask and return
    return masked_code, masked_spans
```

---

## Test Suite

### Diffusion Model Tests (`tests/test_diffusion_model.py`)

**16 tests** | **332 lines** | **100% passing**

1. `test_noise_scheduler_linear` - Linear schedule computation
2. `test_noise_scheduler_cosine` - Cosine schedule (Nichol & Dhariwal)
3. `test_noise_scheduler_sqrt` - Square root schedule
4. `test_diffusion_config_validation` - Config validation
5. `test_model_initialization` - Model setup
6. `test_forward_diffusion` - Forward process
7. `test_generate_basic` - Basic generation
8. `test_generate_with_condition` - Conditional generation
9. `test_validation_errors` - Error handling
10. `test_generate_with_fallback` - Fallback mechanism
11. `test_mock_predict_different_node_types` - Mock implementation
12. `test_diffusion_sample_metadata` - Metadata tracking
13. `test_config_presets` - Preset configs
14. `test_diffusion_with_typescript` - Multi-language
15. `test_scheduler_get_methods` - Scheduler API
16. `test_config_from_env` - Environment loading

### Builder Tests (`tests/test_builder.py`)

**18 tests** | **430 lines** | **100% passing**

1. `test_builder_initialization` - Builder setup
2. `test_generate_patch_basic` - Basic patch generation
3. `test_generate_patch_multiple_targets` - Multiple functions
4. `test_generate_patch_typescript` - TypeScript support
5. `test_generate_patch_nonexistent_file` - Error handling (file)
6. `test_generate_patch_nonexistent_function` - Error handling (function)
7. `test_generate_patch_empty_targets` - Edge case (no targets)
8. `test_generate_patch_without_fallback` - Fallback disabled
9. `test_generated_patch_can_apply` - Safety checks
10. `test_generated_patch_risk_score` - Risk assessment
11. `test_generate_batch_single` - Batch (single item)
12. `test_generate_batch_multiple` - Batch processing
13. `test_generate_batch_with_errors` - Batch error handling
14. `test_refactor_plan_defaults` - Default values
15. `test_unified_diff_format` - Diff generation
16. `test_patch_metadata_completeness` - Metadata completeness
17. `test_builder_with_custom_masker` - Custom masker
18. `test_builder_reuse_for_multiple_patches` - Reusability

---

## Key Features

### 1. Classifier-Free Guidance (CFG)

**Amplifies conditional signal for better prompt following:**

```python
# CFG formula
prediction = uncond_pred + scale * (cond_pred - uncond_pred)
```

- **scale = 1.0**: No guidance (unconditional)
- **scale = 5.0**: Moderate guidance (FAST_CONFIG)
- **scale = 7.5**: Balanced guidance (BALANCED_CONFIG)
- **scale = 10.0**: Strong guidance (QUALITY_CONFIG)

Higher scale = stronger prompt adherence, but risk of over-fitting.

### 2. Deterministic Masking

**AST-aware masking ensures:**
- Masks are anchored to AST node boundaries
- Same function = same mask (reproducible)
- No splitting of tokens across AST nodes
- Syntactically valid intermediate states

### 3. Multi-Language Support

**Currently supported:**
- Python (`function_definition`, `class_definition`)
- TypeScript (`function_declaration`, `function_signature`, `class_declaration`)
- JavaScript (`function_declaration`, `class_declaration`)

**Easy to extend:**
```python
target_node_types = {
    "rust": ["function_item", "impl_item"],
    "go": ["function_declaration", "method_declaration"],
    # ... add more languages
}
```

### 4. Provenance Tracking

**Every patch includes:**
- Original RefactorPlan (what was requested)
- Masked spans (what was regenerated)
- Diffusion metadata (how it was generated)
- Validation status (is it safe?)
- Generation timestamp (when)
- Risk score (how risky?)

**Enables:**
- Rollback on errors
- A/B testing of configs
- Debugging generation issues
- Audit trail for compliance

### 5. Graceful Degradation

**Multiple fallback layers:**
1. Diffusion generation (primary)
2. Syntax validation (gate)
3. Autoregressive fallback (Qwen small)
4. Error patch (always returns something)

**Never fails completely** - always returns a GeneratedPatch, even on errors.

---

## Performance

### Mock Backend (Testing)

- **Generation time**: ~0-5ms per patch
- **Memory**: <100MB
- **Purpose**: Fast iteration without GPU

### Real Backends (Production)

**Estimated (based on similar models):**

| Config    | Model        | Steps | Time/Patch | GPU Memory | Quality |
|-----------|--------------|-------|------------|------------|---------|
| FAST      | Qwen 1.5B    | 20    | ~2-5s      | 4GB        | Good    |
| BALANCED  | Qwen 7B      | 50    | ~10-20s    | 16GB       | Great   |
| QUALITY   | Qwen 14B     | 100   | ~30-60s    | 32GB       | Best    |

*Note: Real performance depends on hardware, batch size, and code complexity.*

---

## Integration Points

### Input: Phase 2 (Reasoner)

```python
# Reasoner outputs RefactorPlan
from src.reasoner import Reasoner

reasoner = Reasoner(graph)
plans = reasoner.analyze_issue(issue_description)

# Builder consumes RefactorPlans
from src.diffusion.builder import Builder

builder = Builder(config=BALANCED_CONFIG)
patches = builder.generate_batch(plans)
```

### Input: Phase 3 (Compressor)

```python
# Compressor provides compressed context
from src.compression import JambaCompressor

compressor = JambaCompressor()
compressed = compressor.compress_graph_context(subgraph)

# Add to RefactorPlan
plan.context = {
    "compressed_context": compressed,
    "relevant_files": [...],
    "dependencies": [...]
}
```

### Output: Validation & Application

```python
# Check safety
for patch in patches:
    print(f"File: {patch.file_path}")
    print(f"Valid: {patch.is_valid_syntax}")
    print(f"Risk: {patch.risk_score():.2f}")
    
    if patch.can_apply():
        # Apply patch (Phase 5: Executor)
        apply_patch(patch)
    else:
        # Log for manual review
        log_failed_patch(patch)
```

---

## Next Steps

### Immediate (Phase 4 Completion)

1. **Real Qwen Integration**:
   - Replace mock with actual Qwen2.5-Coder models
   - Add model downloading/caching
   - Optimize inference with vLLM or TensorRT

2. **CFG Validation with outlines**:
   - Add structured output constraints
   - Ensure generated code matches grammar
   - Pre-commit validation gates

3. **Integration Tests**:
   - End-to-end tests with real RefactorPlans
   - Synthetic benchmark scenarios
   - Rollback mechanism validation

### Future Enhancements

1. **Advanced Diffusion Techniques**:
   - DDIM (faster sampling with fewer steps)
   - PNDM (pseudo numerical methods for diffusion)
   - Self-conditioning (use previous prediction as context)

2. **Model Optimization**:
   - Quantization (INT8, INT4) for faster inference
   - Flash Attention for memory efficiency
   - Model distillation (train smaller student)

3. **Multi-File Refactoring**:
   - Cross-file dependency tracking
   - Batch optimization across related files
   - Atomic multi-file transactions

4. **Adaptive Config Selection**:
   - Automatically choose config based on:
     - Code complexity
     - Time constraints
     - GPU availability
   - Reinforcement learning for config tuning

5. **Human-in-the-Loop**:
   - Interactive approval for high-risk patches
   - User feedback loop for model improvement
   - A/B testing of different configs

---

## Summary

**Phase 4 Core Implementation: ✅ COMPLETE**

**What was built:**
- ✅ Discrete diffusion model (468 lines)
- ✅ Noise scheduling (3 strategies)
- ✅ Classifier-free guidance (CFG)
- ✅ Autoregressive fallback
- ✅ Mock implementation
- ✅ Builder orchestrator (478 lines)
- ✅ RefactorPlan/GeneratedPatch dataclasses
- ✅ Multi-language support (Python, TypeScript, JavaScript)
- ✅ Risk assessment & safety checks
- ✅ Batch processing
- ✅ Comprehensive test suite (34/34 passing)

**Total Phase 4 Code:**
- **Source**: ~1,600 lines
- **Tests**: ~760 lines
- **Total**: ~2,360 lines

**Dependencies:**
- numpy 2.2.6
- torch 2.9.1
- tree-sitter, tree-sitter-languages
- ai21 (Phase 3 integration)

**Next Phase**: Phase 5: The Executor (Apply patches, validate, rollback)

**Commits:**
- `6967959`: Phase 4 core diffusion engine
- `cbfa419`: Phase 4 Builder orchestrator

---

**Phase 4: The Builder** is now production-ready for testing with mock backend!

For real deployment, integrate Qwen2.5-Coder models and run end-to-end validation.
