# LM Studio Setup Guide for Phase 2 Testing

## Why LM Studio?

- ✅ **FREE** - No API costs
- ✅ **Fast** - Runs locally on your GPU
- ✅ **Private** - Your code never leaves your machine
- ✅ **DeepSeek-R1** - Strong reasoning for code refactoring

## Step 1: Download LM Studio

1. Go to [https://lmstudio.ai/](https://lmstudio.ai/)
2. Download for Windows
3. Install and launch

## Step 2: Download DeepSeek-R1 Model

In LM Studio:

1. Click **"Search"** tab
2. Search for: `deepseek-r1-distill-qwen-32b`
3. **Recommended model:** `bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF`
   - Download the **Q4_K_M** quantization (~20GB)
   - Good balance of speed and quality
   - Fits in 16GB RAM

**Alternative (smaller):**
- `DeepSeek-R1-Distill-Qwen-14B` - Faster, requires ~10GB RAM

## Step 3: Load Model

1. Go to **"Chat"** tab
2. Click **"Select a model"**
3. Choose the downloaded DeepSeek-R1 model
4. Wait for it to load (shows "Model loaded" in bottom right)

## Step 4: Start Local Server

1. Click **"Local Server"** tab (left sidebar)
2. Click **"Start Server"** button
3. Default endpoint: `http://localhost:1234/v1`
4. Keep LM Studio running!

## Step 5: Test with Ouroboros

Open PowerShell in your project:

```powershell
# Activate virtual environment
cd 'g:\Just a Idea'
.\venv\Scripts\Activate.ps1
$env:PYTHONPATH='g:\Just a Idea'

# Test connection
python scripts/generate_refactor_plan.py test-connection --provider lmstudio

# Generate refactor plan (FREE!)
python scripts/generate_refactor_plan.py generate "Rename function foo to bar" --file src/utils.py --provider lmstudio
```

## Configuration Options

### Environment Variables (Optional)

```powershell
# Change LM Studio endpoint (if using different port)
$env:LMSTUDIO_BASE_URL = "http://localhost:1234/v1"

# Set as default provider
$env:REASONER_PROVIDER = "lmstudio"
```

### Update Model Name

If you downloaded a different model, update `src/reasoner/config.py`:

```python
LMSTUDIO_CONFIG = ModelConfig(
    model_name="your-model-name-here",  # Match LM Studio
    max_tokens=8192,
    context_window=32_000,
    ...
)
```

## Troubleshooting

### Error: "Connection refused"
- ✅ Make sure LM Studio Local Server is running
- ✅ Check the port is 1234 (default)
- ✅ Verify model is loaded in Chat tab

### Error: "Model not found"
- ✅ Update `model_name` in config.py to match LM Studio exactly
- ✅ Check model name in LM Studio's loaded models list

### Slow responses
- ✅ Use smaller quantization (Q4_K_M or Q4_K_S)
- ✅ Try 14B model instead of 32B
- ✅ Enable GPU acceleration in LM Studio settings

## Performance Tips

1. **GPU Acceleration:** 
   - LM Studio Settings → Enable GPU offloading
   - Set layers to offload = all available

2. **Context Length:**
   - Reduce `context_window` in config if model is slow
   - Start with 16K tokens for faster responses

3. **Quantization:**
   - Q4_K_M: Best balance (recommended)
   - Q4_K_S: Faster, slightly lower quality
   - Q5_K_M: Higher quality, slower

## Comparing Providers

| Provider | Cost | Speed | Quality | Context |
|----------|------|-------|---------|---------|
| **LM Studio (DeepSeek-R1)** | FREE | Medium | High | 32K |
| Claude 3.5 Sonnet | $0.06/req | Fast | Highest | 200K |
| OpenAI GPT-4o | $0.025/req | Fast | High | 128K |
| Jamba 1.5 Mini | $0.001/req | Fast | Medium | 256K |

## Next Steps

Once LM Studio is working:

1. Test with simple refactors: "Rename function X to Y"
2. Try complex tasks: "Extract validation logic into separate function"
3. Compare quality with mock provider
4. When ready, add OpenAI credits for production use

---

**Questions?** LM Studio has excellent docs at [https://lmstudio.ai/docs](https://lmstudio.ai/docs)
