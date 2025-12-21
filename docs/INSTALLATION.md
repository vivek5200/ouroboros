# Ouroboros Installation Guide

## Quick Install (5 minutes)

### 1. Prerequisites
- Python 3.10 or higher
- Git
- Docker (optional - for Neo4j graph database)

### 2. Clone Repository
```bash
git clone <repository-url>
cd ouroboros
```

### 3. Create Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Test Installation
```bash
# Windows
.\ouroboros.bat --help

# Linux/Mac
chmod +x ouroboros.sh
./ouroboros.sh --help

# Or directly
python ouroboros_cli.py --help
```

You should see:
```
🐍 Ouroboros - AI-Powered Code Refactoring with Discrete Diffusion

Usage: ouroboros [OPTIONS] COMMAND [ARGS]...

Commands:
  refactor    🔧 Refactor code using Ouroboros AI pipeline
  status      📊 Check status of a generation run
  list-runs   📝 List recent generation runs
```

## Detailed Setup

### Option 1: Mock Mode (No External Services)
Perfect for testing and development without API keys or databases.

```bash
# Test with mock mode
python ouroboros_cli.py refactor "Add caching" \
  --target src/example.py \
  --mock \
  --dry-run
```

**Pros**:
- No API keys needed
- No database required
- Instant setup
- Safe for testing

**Cons**:
- Generates mock code (not real refactoring)
- Limited functionality

### Option 2: Full Setup (Production)
Complete setup with all features.

#### Step 1: Start Neo4j (Knowledge Graph)
```bash
# Using Docker
docker-compose up -d

# Verify Neo4j is running
docker ps

# Access Neo4j Browser
# URL: http://localhost:7474
# User: neo4j
# Password: ouroboros123
```

#### Step 2: Initialize Database
```bash
python scripts/init_schema.py
```

#### Step 3: Get API Keys (Optional)

**AI21 API Key** (for Jamba context compression):
1. Sign up at https://www.ai21.com/
2. Get API key from dashboard
3. Set environment variable:
   ```bash
   # Windows
   set AI21_API_KEY=your_key_here
   
   # Linux/Mac
   export AI21_API_KEY=your_key_here
   ```

**Anthropic API Key** (for Claude reasoning):
1. Sign up at https://www.anthropic.com/
2. Get API key from console
3. Set environment variable:
   ```bash
   # Windows
   set ANTHROPIC_API_KEY=your_key_here
   
   # Linux/Mac
   export ANTHROPIC_API_KEY=your_key_here
   ```

#### Step 4: Run Full Pipeline
```bash
python ouroboros_cli.py refactor "Add error handling" \
  --target src/api.py \
  --config balanced \
  --safe-mode \
  --auto-apply \
  --max-risk 0.3
```

## Verification

### Test 1: Syntax Validator
```bash
python src/utils/syntax_validator.py
```

Expected output:
```
================================================================================
Syntax Validator - Phase 5 Safety Gate
================================================================================

Supported languages: python, javascript, typescript

Validating VALID Python code:
  Is valid: True
  Parse time: 12.34ms
  Summary: No syntax errors

Validating INVALID Python code:
  Is valid: False
  Parse time: 15.67ms
  Summary: 3 syntax errors; First error at line 2: Syntax error
```

### Test 2: Provenance Logger
```bash
python src/utils/provenance_logger.py
```

Expected output:
```
================================================================================
Provenance Logger - Phase 5 Auditability
================================================================================

Run ID: gen_20250121_123456_abc123
Started: 2025-12-21T15:30:00

...

Saved to: ./artifact_metadata_example.json
```

### Test 3: CLI Help
```bash
python ouroboros_cli.py --help
```

Should show command list and options.

### Test 4: Mock Refactor
```bash
python ouroboros_cli.py refactor "Test refactoring" \
  --target README.md \
  --mock \
  --dry-run
```

Should complete without errors and show results.

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'tree_sitter'"
**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "Failed to initialize Python parser"
**Solution**: Install tree-sitter language bindings
```bash
pip install tree-sitter-python tree-sitter-javascript tree-sitter-typescript
```

### Issue: "No target files specified"
**Solution**: Add `--target` flag
```bash
# ❌ Wrong
ouroboros refactor "Add caching"

# ✅ Correct
ouroboros refactor "Add caching" --target src/file.py
```

### Issue: "Neo4j connection failed"
**Solution**: Use mock mode or start Neo4j
```bash
# Option 1: Mock mode
python ouroboros_cli.py refactor "Task" -t file.py --mock

# Option 2: Start Neo4j
docker-compose up -d
```

### Issue: Permission denied on ouroboros.sh
**Solution**: Make script executable
```bash
chmod +x ouroboros.sh
```

## Configuration Files

### .env (Optional)
Create `.env` file in project root:
```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=ouroboros123

# API Keys (Optional)
AI21_API_KEY=your_ai21_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
```

### config.yaml (Optional)
Advanced configuration for generation:
```yaml
# See src/diffusion/config.py for options
diffusion:
  backbone: "mock"  # or "gpt4", "claude"
  num_sampling_steps: 50
  cfg_guidance_scale: 2.0
  
safety:
  enable_safety_gate: true
  max_retry_attempts: 3
  
cli:
  default_config: "balanced"
  default_max_risk: 0.5
```

## System Requirements

### Minimum
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 1 GB free space
- **Python**: 3.10+

### Recommended
- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Disk**: 5 GB free space
- **Python**: 3.11+
- **Docker**: For Neo4j

### Optional Services
- **Neo4j**: Graph database (4 GB RAM recommended)
- **API Access**: AI21, Anthropic, or OpenAI

## Directory Structure After Installation

```
ouroboros/
├── venv/                      # Virtual environment
├── artifacts/                 # Generated provenance files
├── src/                       # Source code
├── tests/                     # Test suite
├── docs/                      # Documentation
├── ouroboros_cli.py          # Main CLI
├── ouroboros.bat             # Windows launcher
├── ouroboros.sh              # Unix launcher
├── requirements.txt          # Dependencies
├── docker-compose.yml        # Neo4j container
└── .env                      # Environment variables (optional)
```

## First Run Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] CLI help works (`python ouroboros_cli.py --help`)
- [ ] Syntax validator tested
- [ ] Provenance logger tested
- [ ] Mock mode works
- [ ] (Optional) Neo4j running
- [ ] (Optional) API keys configured

## Getting Help

### Documentation
- [PHASE_5_COMPLETE.md](PHASE_5_COMPLETE.md) - Comprehensive guide
- [CLI_QUICK_REFERENCE.md](CLI_QUICK_REFERENCE.md) - Quick reference
- [README.md](README.md) - Main documentation

### CLI Help
```bash
# General help
python ouroboros_cli.py --help

# Command-specific help
python ouroboros_cli.py refactor --help
python ouroboros_cli.py status --help
python ouroboros_cli.py list-runs --help
```

### Example Runs
```bash
# Start with mock mode dry-run
python ouroboros_cli.py refactor "Test task" \
  --target README.md \
  --mock \
  --dry-run

# Check status
python ouroboros_cli.py status --latest

# List runs
python ouroboros_cli.py list-runs
```

## Success!

If you can run this command successfully, you're ready to go:

```bash
python ouroboros_cli.py refactor "Add caching" \
  --target src/example.py \
  --mock \
  --dry-run
```

**Congratulations! Ouroboros is installed and ready to use!** 🎉

## Next Steps

1. Read [CLI_QUICK_REFERENCE.md](CLI_QUICK_REFERENCE.md) for usage examples
2. Try mock mode on a real file
3. Set up Neo4j for full functionality (optional)
4. Configure API keys for real AI models (optional)
5. Run your first real refactoring!
