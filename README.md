# 🐍 Ouroboros - AI-Powered Code Refactoring with Discrete Diffusion

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Neo4j 5.15](https://img.shields.io/badge/neo4j-5.15-brightgreen.svg)](https://neo4j.com/)
[![Phase 5 Complete](https://img.shields.io/badge/Phase%205-Complete-success.svg)](PHASE_5_COMPLETE.md)

**Version:** 2.0.0  
**Date:** December 21, 2025  
**Author:** Vivek Bendre

## Overview

Ouroboros is a production-ready AI code generation system that combines:
- **GraphRAG** for infinite, deterministic context
- **Discrete Diffusion** for high-quality code generation
- **Safety Gates** with Tree-Sitter syntax validation
- **Self-Healing** retry loops
- **Complete Provenance** logging for auditability

## ✨ Quick Start

### Install

```bash
pip install -r requirements.txt
```

### Refactor Code

```bash
# Basic usage
python ouroboros_cli.py refactor "Add caching to user service" \
  --target src/user_service.py

# Auto-apply safe changes
python ouroboros_cli.py refactor "Add type hints" \
  -t src/utils.py \
  --auto-apply \
  --max-risk 0.3

# Preview changes (dry run)
python ouroboros_cli.py refactor "Optimize queries" \
  -t src/db.py \
  --dry-run
```

### Check Status

```bash
# View latest run
python ouroboros_cli.py status --latest

# List recent runs
python ouroboros_cli.py list-runs
```

See [CLI Quick Reference](CLI_QUICK_REFERENCE.md) for more examples.

## 🏗️ Architecture

Ouroboros implements a 5-phase pipeline:

### Phase 1: The Librarian (Knowledge Graph)
✅ **Complete** - Neo4j-based structural memory with provenance tracking
- Graph database for code relationships
- Tree-sitter parsing for multiple languages
- Deterministic context retrieval

### Phase 2: The Reasoner (Analysis & Planning)
✅ **Complete** - Dependency analysis and refactor planning
- Analyzes code dependencies
- Creates prioritized refactor plans
- Impact assessment

### Phase 3: The Compressor (Context Encoding)
✅ **Complete** - Jamba 1.5 Mini for context compression
- Compresses context to fit token limits
- Preserves critical information
- Optimized for long-context tasks

### Phase 4: The Builder (Code Generation)
✅ **Complete** - Discrete diffusion for code generation
- High-quality code generation
- Multiple backbone options (Mock/GPT/Claude)
- AST-aware masking and generation

### Phase 5: The Integration Loop (Safety & UX)
✅ **Complete** - Safety gates, CLI, and provenance
- **Safety Gate**: Tree-Sitter syntax validation
- **Self-Healing**: Automatic retry on errors
- **CLI**: Beautiful terminal interface (Typer + Rich)
- **Provenance**: Complete auditability logs

See [Phase 5 Complete](docs/PHASE_5_COMPLETE.md) for detailed documentation.

## 📁 Project Structure

```
ouroboros/
├── ouroboros_cli.py              # 🎯 Main CLI entry point
├── ouroboros.bat                 # Windows launcher
├── ouroboros.sh                  # Unix/Linux launcher
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── docker-compose.yml            # Neo4j setup
├── .env.example                  # Environment template
├──
├── src/                          # Source code
│   ├── ouroboros_pipeline.py     # End-to-end pipeline orchestration
│   ├── librarian/                # Phase 1: Knowledge Graph
│   │   ├── graph_db.py          # Neo4j operations
│   │   ├── parser.py            # Tree-sitter parsing
│   │   ├── graph_constructor.py # Graph building
│   │   ├── retriever.py         # Context retrieval
│   │   └── provenance.py        # Metadata tracking
│   ├── reasoner/                 # Phase 2: Analysis & Planning
│   │   ├── reasoner.py          # Main reasoner
│   │   ├── dependency_analyzer.py
│   │   ├── llm_client.py        # LLM integration
│   │   └── plan_parser.py
│   ├── context_encoder/          # Phase 3: Compression
│   │   ├── encoder.py           # Jamba integration
│   │   ├── config.py
│   │   └── validator.py
│   ├── diffusion/                # Phase 4: Generation
│   │   ├── builder.py           # 🛡️ High-level orchestrator with safety gate
│   │   ├── diffusion_model.py   # Discrete diffusion implementation
│   │   ├── masking.py           # AST-aware masking
│   │   └── config.py
│   ├── architect/                # Schema definitions
│   │   └── schemas.py
│   └── utils/                    # Phase 5: Safety & Utilities
│       ├── syntax_validator.py  # 🛡️ Tree-Sitter validation
│       ├── provenance_logger.py # 📊 Audit logging
│       └── checksum.py
│
├── scripts/                      # Utility scripts
│   ├── init_schema.py           # Database schema initialization
│   ├── ingest.py                # Code ingestion
│   ├── run_graph_construct.py   # Graph construction
│   └── verify_*.py              # Verification scripts
│
├── tests/                        # Test suite
│   ├── test_*.py                # Unit tests
│   └── synthetic_benchmarks/    # Integration tests
│
├── docs/                         # 📚 Documentation
│   ├── index.md                 # Documentation index
│   ├── INSTALLATION.md          # Setup guide
│   ├── CLI_QUICK_REFERENCE.md   # CLI reference
│   ├── PHASE_4_COMPLETE.md      # Phase 4 documentation
│   ├── PHASE_5_COMPLETE.md      # Phase 5 documentation
│   ├── PHASE_5_SUMMARY.md       # Implementation summary
│   ├── GITHUB_SETUP.md          # GitHub guide
│   └── ...                      # Other documentation
│
├── examples/                     # Example scripts
│   └── example_e2e_generation.py
│
└── artifacts/                    # Generated files (gitignored)
    └── artifact_metadata_*.json  # Provenance logs
```
├── docker-compose.yml          # Neo4j container configuration
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
├── scripts/
│   ├── init_schema.py         # Database schema initialization
│   ├── ingest.py              # Code ingestion pipeline
│   └── query.py               # Graph traversal queries
├── src/
│   ├── librarian/             # Core GraphRAG implementation
│   │   ├── __init__.py
│   │   ├── graph_db.py        # Neo4j connection & operations
│   │   ├── parser.py          # Tree-sitter code parsing
│   │   ├── provenance.py      # Metadata tracking
│   │   └── retrieval.py       # Subgraph extraction
│   └── utils/
│       ├── __init__.py
│       └── checksum.py        # File hashing utilities
└── tests/
    └── synthetic_benchmarks/   # Validation test suite
        ├── rename_import/
        ├── move_function/
        └── change_signature/
```

## 🔑 Key Features

### 🛡️ Safety Gate
- Tree-Sitter syntax validation before ANY code touches disk
- Self-healing retry loop (up to 3 attempts)
- Detailed error reporting with line numbers and context
- Zero invalid syntax reaches your codebase

### 🖥️ Beautiful CLI
- Rich terminal output with tables and progress bars
- Interactive and scriptable
- Dry-run mode to preview changes
- Auto-apply for low-risk patches

### 📊 Complete Provenance
Every run generates `artifact_metadata.json`:
- Which AI models did what (Reasoner, Compressor, Generator)
- All safety checks performed
- Files modified with hashes and diffs
- Complete timing and token usage

### ⚡ Smart Generation
- **Fast mode**: 10 steps (~2s)
- **Balanced mode**: 50 steps (~8s) - recommended
- **Quality mode**: 100 steps (~15s)

## 📁 Project Structure

```
ouroboros/
├── ouroboros_cli.py              # 🎯 Main CLI entry point
├── src/
│   ├── ouroboros_pipeline.py     # End-to-end pipeline
│   ├── librarian/                # Phase 1: Knowledge Graph
│   │   ├── graph_db.py          # Neo4j operations
│   │   ├── parser.py            # Tree-sitter parsing
│   │   ├── retriever.py         # Graph retrieval
│   │   └── provenance.py        # Metadata tracking
│   ├── reasoner/                 # Phase 2: Analysis
│   │   ├── dependency_analyzer.py
│   │   ├── llm_client.py
│   │   └── plan_parser.py
│   ├── context_encoder/          # Phase 3: Compression
│   │   ├── encoder.py           # Jamba integration
│   │   └── config.py
│   ├── diffusion/                # Phase 4: Generation
│   │   ├── builder.py           # High-level orchestrator
│   │   ├── diffusion_model.py   # Discrete diffusion
│   │   ├── masking.py           # AST masking
│   │   └── config.py
│   └── utils/                    # Phase 5: Safety & Provenance
│       ├── syntax_validator.py  # 🛡️ Tree-Sitter validation
│       └── provenance_logger.py # 📊 Audit logging
├── artifacts/                    # Generated provenance files
├── tests/                        # Test suite
└── docs/                         # Documentation

```

## 🚀 Usage Examples

### Example 1: Add Caching

```bash
python ouroboros_cli.py refactor "Add caching to user lookup" \
  --target src/user_service.py \
  --auto-apply \
  --max-risk 0.3
```

**What happens:**
1. Analyzes `src/user_service.py` and dependencies
2. Creates refactor plan with impact analysis
3. Compresses context with Jamba (if configured)
4. Generates code with discrete diffusion
5. **Safety Gate**: Validates syntax with Tree-Sitter
6. Auto-retries if syntax errors (up to 3 times)
7. Auto-applies patches with risk ≤ 0.3
8. Creates backup (`.backup` files)
9. Logs everything to `artifacts/artifact_metadata_*.json`

### Example 2: Optimize Performance

```bash
python ouroboros_cli.py refactor "Optimize database queries" \
  --target src/db.py \
  --target src/cache.py \
  --config quality \
  --dry-run
```

**What happens:**
1. Analyzes both files
2. Uses quality config (100 diffusion steps)
3. Shows what would be changed
4. Does NOT modify files (dry-run)

### Example 3: Check What Was Done

```bash
python ouroboros_cli.py status --latest
```

**Shows:**
```
╭─────────── Provenance Metadata ───────────╮
│ ✓ Run ID: gen_20250121_123456             │
│ Task: Add caching to user lookup          │
│ Duration: 8.5s                            │
│ Status: Success                           │
╰───────────────────────────────────────────╯

              Models Used              
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Phase     ┃ Model            ┃ Time   ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ reasoner  │ claude-3.5       │ 2500ms │
│ compressor│ jamba-1.5-mini   │ 1200ms │
│ generator │ diffusion-model  │ 5500ms │
└───────────┴──────────────────┴────────┘

              Safety Checks              
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Type              ┃ Status ┃ Details      ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━┩
│ syntax_validation │   ✓    │ No errors    │
└───────────────────┴────────┴──────────────┘
```

## 🛡️ Safety Features

### 1. Syntax Validation
Every generated code is validated with Tree-Sitter **before** touching disk:
```python
validator = SyntaxValidator()
result = validator.validate(generated_code, language="python")

if result.is_valid:
    apply_to_disk()
else:
    retry_with_error_feedback()
```

### 2. Self-Healing Retry
If syntax errors detected:
1. Extract error details (line number, type, context)
2. Enhance generation prompt with error feedback
3. Retry generation (up to 3 attempts)
4. Log all retry attempts in provenance

### 3. Risk Scoring
Each patch gets a risk score (0.0-1.0):
- Invalid syntax: +0.5
- Validation errors: +0.3
- Large changes (>100 lines): +0.2

Only patches below `--max-risk` threshold are auto-applied.

### 4. Automatic Backups
Before applying any patch:
- Original saved as `<file>.backup`
- SHA256 hash recorded in provenance
- Rollback always possible

## Node Types

- `:File` - Source code files
- `:Class` - Class definitions
- `:Function` - Function/method definitions
- `:Variable` - Variable declarations
- `:Import` - Import statements

## Edge Types

- `[:IMPORTS]` - File imports another file
- `[:INHERITS_FROM]` - Class inheritance
- `[:CALLS]` - Function calls another function
- `[:INSTANTIATES]` - Creates instance of class
- `[:CONTAINS]` - File contains class/function

## Usage

### Ingest a Codebase

```powershell
python scripts/ingest.py --path ./your-project --language typescript
```

### Query Dependencies

```powershell
python scripts/query.py --file src/auth.ts --depth 2
```

### Run Synthetic Tests

```powershell
python -m pytest tests/synthetic_benchmarks/
```

## Next Steps

- [ ] Phase 2: The Architect (Reasoning Layer)
- [ ] Phase 3: The Context Encoder (Mamba Layer)
- [ ] Phase 4: The Builder (Generation Layer)
- [ ] Phase 5: Full Integration

## References

- Edge, D., et al. (2024). From Local to Global: A Graph RAG Approach. [arXiv:2404.16130]
- Neo4j Documentation: https://neo4j.com/docs/
- LangChain Neo4j Integration: https://python.langchain.com/docs/integrations/graphs/neo4j_cypher

## License

MIT License - Research & Development
