# AI21 Jamba Cloud Setup Guide

## Why AI21 Cloud?

✅ **Recommended for Production**
- Reliable 99.9% uptime
- No local GPU required
- Automatic scaling
- 256k token context window
- Official support from AI21

## Step 1: Get Your API Key

1. Go to [AI21 Studio](https://studio.ai21.com/)
2. Sign up / Log in
3. Navigate to **Account → API Key**
4. Click **"Create New API Key"**
5. Copy your API key (starts with `AI21_...`)

**Free Tier:**
- $10 free credits on signup
- ~200,000 tokens free
- Good for testing Phase 3

**Pricing (after free tier):**
- Jamba-1.5-Mini: $0.20 per 1M input tokens
- Jamba-1.5-Large: $2.00 per 1M input tokens

## Step 2: Configure Ouroboros

### Option A: Environment Variable (Recommended)

```bash
# Windows PowerShell
$env:AI21_API_KEY="your_api_key_here"

# Linux/Mac
export AI21_API_KEY="your_api_key_here"
```

### Option B: .env File

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your key
AI21_API_KEY=your_actual_api_key_here
JAMBA_MODE=cloud
```

## Step 3: Test the Connection

```python
from src.context_encoder import ContextEncoder, ContextEncoderConfig
from src.context_encoder.config import EncoderProvider, JambaConfig

# Configure for AI21 Cloud
jamba_config = JambaConfig(
    use_cloud=True,
    cloud_api_key="your_api_key_here"  # Or load from env
)

config = ContextEncoderConfig(
    provider=EncoderProvider.JAMBA_CLOUD,
    jamba=jamba_config
)

encoder = ContextEncoder(config)

# Test compression
sample_code = """
export class AuthService {
    async login(email: string, password: string) {
        // Authentication logic
    }
}
"""

compressed = encoder.compress(
    codebase_context=sample_code,
    target_files=["auth.ts"]
)

print(f"✅ Compression successful!")
print(f"Input: {compressed.tokens_in} tokens")
print(f"Output: {compressed.tokens_out} tokens")
print(f"Ratio: {compressed.compression_ratio:.1f}x")
print(f"\nSummary:\n{compressed.summary}")
```

## Step 4: Use with Reasoner (Phase 2 Integration)

```python
from src.reasoner import Reasoner, ReasonerConfig
from src.reasoner.config import LLMProvider

# Initialize Reasoner
config = ReasonerConfig(provider=LLMProvider.GEMINI)
reasoner = Reasoner(config)

# Generate refactor plan with deep context
plan = reasoner.generate_refactor_plan(
    task_description="Refactor authentication system",
    target_file="src/auth/login.ts",
    use_deep_context=True  # 🔥 Uses AI21 Jamba for 256k context
)

print(f"Plan ID: {plan.plan_id}")
print(f"Impact: {plan.estimated_impact}")
```

## Troubleshooting

### Error: "AI21_API_KEY environment variable not set"

**Solution:** Set the environment variable or pass it explicitly:

```python
from src.context_encoder.config import JambaConfig

jamba_config = JambaConfig(
    use_cloud=True,
    cloud_api_key="your_key_here"
)
```

### Error: "Failed to initialize Jamba client"

**Possible causes:**
1. Invalid API key
2. No internet connection
3. AI21 API is down (check [status.ai21.com](https://status.ai21.com))

**Solution:** Verify your API key at [studio.ai21.com](https://studio.ai21.com)

### Error: Rate limit exceeded

**Solution:** You've used your free credits. Options:
1. Add payment method to AI21 account
2. Switch to local mode (free): `JAMBA_MODE=local`
3. Use mock provider for testing: `EncoderProvider.MOCK`

### Slow response times

**Normal behavior:**
- First request: 10-30 seconds (cold start)
- Subsequent requests: 3-10 seconds
- Large context (100k+ tokens): 15-45 seconds

**If consistently slow:**
- Check your internet connection
- Try a smaller context first
- Consider using `max_output_tokens` to limit summary length

## Switching Between Cloud and Local

### Use Cloud (Recommended)

```python
config = ContextEncoderConfig(
    provider=EncoderProvider.JAMBA_CLOUD,
    jamba=JambaConfig(use_cloud=True)
)
```

### Use Local (Free, Requires LM Studio)

```python
config = ContextEncoderConfig(
    provider=EncoderProvider.JAMBA_LOCAL,
    jamba=JambaConfig(
        use_cloud=False,
        local_base_url="http://localhost:1234/v1"
    )
)
```

See [LMSTUDIO_SETUP.md](./LMSTUDIO_SETUP.md) for local setup instructions.

## Cost Estimation

**Jamba-1.5-Mini Pricing:**

| Context Size | Input Tokens | Output Tokens | Cost per Request |
|--------------|--------------|---------------|------------------|
| Small (10k)  | 10,000       | 2,000         | $0.002           |
| Medium (50k) | 50,000       | 4,000         | $0.010           |
| Large (100k) | 100,000      | 4,000         | $0.020           |
| Massive (256k)| 256,000     | 4,000         | $0.051           |

**Free tier gives you:**
- ~5,000 requests (small context)
- ~1,000 requests (medium context)
- ~500 requests (large context)
- ~200 requests (massive context)

## Best Practices

1. **Start with mock provider** for development:
   ```python
   config = ContextEncoderConfig(provider=EncoderProvider.MOCK)
   ```

2. **Use cloud for production** (reliable, scalable)

3. **Use local for experimentation** (free, private)

4. **Monitor your usage** at [studio.ai21.com](https://studio.ai21.com)

5. **Cache compressed contexts** to avoid redundant API calls

## Security

⚠️ **Never commit your API key to Git!**

- ✅ Use environment variables
- ✅ Use `.env` file (in `.gitignore`)
- ❌ Don't hardcode keys in source code
- ❌ Don't share keys in screenshots/logs

## Support

- **AI21 Documentation:** https://docs.ai21.com/
- **AI21 Discord:** https://discord.gg/ai21labs
- **GitHub Issues:** https://github.com/vivek5200/ouroboros/issues
