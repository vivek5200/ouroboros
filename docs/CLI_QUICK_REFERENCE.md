# Ouroboros CLI Quick Reference

## Installation

```bash
pip install -r requirements.txt
```

## Basic Commands

### Refactor Code

```bash
# Basic refactoring
ouroboros refactor "Add caching to user service" --target src/user_service.py

# With auto-apply for safe changes
ouroboros refactor "Add type hints" -t src/utils.py --auto-apply --max-risk 0.3

# Multiple files, quality mode
ouroboros refactor "Optimize queries" -t src/db.py -t src/cache.py -c quality

# Dry run (preview only)
ouroboros refactor "Migrate to async" -t src/api.py --dry-run
```

### Check Status

```bash
# View latest run
ouroboros status --latest

# Check specific run
ouroboros status --run-id gen_20250121_123456
```

### List Runs

```bash
# Show recent runs
ouroboros list-runs

# Show more runs
ouroboros list-runs --limit 20
```

## Key Options

### `refactor` Command

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--target` | `-t` | Target file to refactor | Required |
| `--function` | `-f` | Specific function to refactor | All |
| `--config` | `-c` | Config: fast/balanced/quality | balanced |
| `--safe-mode` | | Enable syntax validation | True |
| `--max-risk` | | Max risk for auto-apply (0.0-1.0) | 0.5 |
| `--auto-apply` | | Auto-apply safe patches | False |
| `--dry-run` | | Preview without changes | False |
| `--mock` | | Use mock mode (testing) | False |

### Configuration Modes

- **`fast`**: Fastest generation (10 steps)
- **`balanced`**: Good quality/speed tradeoff (50 steps)
- **`quality`**: Best quality (100 steps)

### Risk Scores

- **0.0 - 0.3**: Low risk (safe to auto-apply)
- **0.3 - 0.5**: Medium risk (review recommended)
- **0.5 - 1.0**: High risk (manual review required)

## Examples

### Example 1: Safe Auto-Apply

```bash
ouroboros refactor "Add docstrings" \
  --target src/utils.py \
  --auto-apply \
  --max-risk 0.2 \
  --safe-mode
```

**What happens:**
1. Analyzes `src/utils.py`
2. Generates patches with docstrings
3. Validates syntax (safety gate)
4. Auto-applies patches with risk ≤ 0.2
5. Creates backups (`.backup` files)
6. Logs to `artifacts/artifact_metadata_*.json`

### Example 2: Preview Changes

```bash
ouroboros refactor "Refactor for performance" \
  --target src/slow_function.py \
  --config quality \
  --dry-run
```

**What happens:**
1. Generates high-quality patches
2. Shows what would be changed
3. Does NOT modify files
4. Displays diffs in terminal

### Example 3: Multiple Files

```bash
ouroboros refactor "Add error handling" \
  --target src/api.py \
  --target src/db.py \
  --target src/utils.py \
  --config balanced
```

**What happens:**
1. Analyzes all 3 files
2. Creates refactor plan for each
3. Generates patches with safety validation
4. Shows results for manual review

### Example 4: Check What Was Done

```bash
# After running a refactor
ouroboros status --latest
```

**Shows:**
- Models used (Reasoner, Compressor, Generator)
- Safety checks performed  
- Files modified
- Lines added/removed
- Complete provenance metadata

## Provenance Artifacts

Every run creates: `./artifacts/artifact_metadata_<run_id>.json`

Contains:
- **Models used**: Which AI did what
- **Safety checks**: Syntax validation results
- **File changes**: Hashes, diffs, backups
- **Timing**: Duration of each phase
- **Metadata**: Tokens used, retries, etc.

## Safety Features

### 1. Syntax Validation (Safety Gate)

Before ANY code touches disk:
- ✅ Parsed with Tree-Sitter
- ✅ Syntax errors detected
- ✅ Exact error locations identified

### 2. Self-Healing Retry

If syntax errors found:
1. Extract error details
2. Enhance generation prompt with errors
3. Retry generation (up to 3 attempts)
4. Log all retry attempts

### 3. Risk Scoring

Each patch gets risk score (0.0-1.0):
- Invalid syntax: +0.5
- Validation errors: +0.3
- Large changes (>100 lines): +0.2

### 4. Backups

When applying patches:
- Original saved as `.backup`
- Hash recorded in provenance
- Rollback possible

## Troubleshooting

### "No target files specified"

```bash
# ❌ Wrong
ouroboros refactor "Add caching"

# ✅ Correct
ouroboros refactor "Add caching" --target src/file.py
```

### "Invalid config"

```bash
# ❌ Wrong
ouroboros refactor "Task" -t file.py -c turbo

# ✅ Correct (use: fast, balanced, or quality)
ouroboros refactor "Task" -t file.py -c fast
```

### "Syntax validation failed"

The safety gate prevented invalid code!

**What to do:**
1. Check logs for error details
2. System will auto-retry (up to 3 times)
3. If still fails, review generated code manually
4. Check provenance in `artifacts/` folder

### "High risk patches"

Patches with risk > 0.5 need manual review.

**What to do:**
```bash
# 1. Preview the changes
ouroboros refactor "..." -t file.py --dry-run

# 2. Review provenance
ouroboros status --latest

# 3. Apply manually if safe
# (patches are in the result, backup created)
```

## Advanced Usage

### Custom Neo4j Connection

```bash
ouroboros refactor "Task" \
  --target file.py \
  --neo4j-uri bolt://my-server:7687 \
  --neo4j-user admin \
  --neo4j-password secret
```

### With AI21 API Key (for Jamba compression)

```bash
export AI21_API_KEY="your_key_here"

ouroboros refactor "Task" \
  --target file.py \
  --ai21-key $AI21_API_KEY
```

### Mock Mode (Testing)

```bash
# No API calls, no database
ouroboros refactor "Task" \
  --target file.py \
  --mock \
  --dry-run
```

## Best Practices

1. **Start with dry-run**: Preview changes before applying
2. **Use balanced config**: Good tradeoff for most tasks
3. **Set appropriate max-risk**: Lower for critical code
4. **Review provenance**: Check what models did
5. **Keep backups**: Don't delete `.backup` files immediately
6. **Check status often**: Monitor successful/failed runs

## Quick Tips

- 💡 Use `--auto-apply` with low `--max-risk` for safe automation
- 💡 Always `--dry-run` first on critical code
- 💡 Check `--latest` status after each run
- 💡 Review provenance files in `artifacts/` for debugging
- 💡 Safety gate prevents invalid code - let it do its job!

## Getting Help

```bash
# Main help
ouroboros --help

# Command-specific help
ouroboros refactor --help
ouroboros status --help
ouroboros list-runs --help
```

## File Locations

- **Provenance**: `./artifacts/artifact_metadata_*.json`
- **Backups**: `<original_file>.backup`
- **Logs**: Console output (configure logging as needed)

## Exit Codes

- `0`: Success
- `1`: Error (check logs for details)
