# 🐍 Ouroboros - AI-Powered Code Refactoring with Discrete Diffusion

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Neo4j 5.15](https://img.shields.io/badge/neo4j-5.15-brightgreen.svg)](https://neo4j.com/)
[![Phase 5 Complete](https://img.shields.io/badge/Phase%205-Complete-success.svg)](docs/PHASE_5_COMPLETE.md)

**Version:** 2.0.0  
**Date:** December 21, 2025  
**Author:** Vivek Bendre

---

## 🎯 Overview

Ouroboros is a **production-ready autonomous software engineering system** that transforms natural language instructions into safe, high-quality code refactorings. It combines cutting-edge AI techniques with rigorous safety mechanisms:

### Core Technologies
- 🧠 **GraphRAG Knowledge Base** - Neo4j-powered structural memory for infinite, deterministic context
- 🎨 **Discrete Diffusion Code Generation** - High-quality code synthesis using denoising diffusion
- 🛡️ **Tree-Sitter Safety Gates** - Syntax validation before any code touches disk
- 🔄 **Self-Healing Retry Loops** - Automatic error recovery with contextual feedback
- 📊 **Complete Provenance Logging** - Full auditability for every operation

### What Makes Ouroboros Different?
1. **Safe by Default**: Every generated code is syntax-validated before touching disk
2. **Graph-Aware**: Understands code relationships through Neo4j knowledge graph
3. **Self-Improving**: Automatically retries with error feedback when generation fails
4. **Production-Ready**: Complete CLI, provenance logging, and risk scoring
5. **Multi-Language**: Supports Python, JavaScript, and TypeScript

---

## ✨ Quick Start

### Installation (5 minutes)

```bash
# 1. Clone repository
git clone <repository-url>
cd ouroboros

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate    # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Test installation
python ouroboros_cli.py --help
```

### Your First Refactoring

```bash
# Basic usage - Add caching to a service
python ouroboros_cli.py refactor "Add caching to user lookups" \
  --target src/user_service.py \
  --dry-run

# Auto-apply safe changes
python ouroboros_cli.py refactor "Add type hints to all functions" \
  --target src/utils.py \
  --auto-apply \
  --max-risk 0.3

# Preview changes in quality mode
python ouroboros_cli.py refactor "Optimize database queries" \
  --target src/db.py \
  --config quality \
  --dry-run
```

### Check What Was Done

```bash
# View latest run details
python ouroboros_cli.py status --latest

# List all recent runs
python ouroboros_cli.py list-runs
```

📚 **See [CLI Quick Reference](docs/CLI_QUICK_REFERENCE.md) for more examples**  
📖 **See [Installation Guide](docs/INSTALLATION.md) for detailed setup**

---

## 🏗️ Architecture - The 5 Phases

Ouroboros implements a **5-phase autonomous software engineering pipeline** where each phase builds upon the previous one:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Phase 1:   │───▶│  Phase 2:   │───▶│  Phase 3:   │───▶│  Phase 4:   │───▶│  Phase 5:   │
│  Librarian  │    │  Reasoner   │    │ Compressor  │    │   Builder   │    │ Integration │
│   (Graph)   │    │  (Analysis) │    │  (Context)  │    │ (Diffusion) │    │   (Safety)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
   Knowledge           Planning          Compression          Generation          Safety
```

### Phase 1: The Librarian 📚
**Status:** ✅ Complete ([Details](docs/PHASE1_COMPLETE.md))

**Purpose:** Build a GraphRAG knowledge base for deterministic, graph-aware code understanding

**Key Components:**
- **Neo4j Graph Database** - Stores code structure as graph (Files, Classes, Functions)
- **Tree-Sitter Parser** - Multi-language AST extraction (Python, JavaScript, TypeScript)
- **Graph Constructor** - Builds relationships (IMPORTS, CALLS, INHERITS_FROM)
- **Provenance Tracker** - Logs all metadata (checksums, timestamps, model versions)
- **Graph Retriever** - Subgraph extraction for relevant context

**Deliverables:**
- 10 synthetic benchmarks demonstrating refactoring capabilities
- 100% test pass rate across 4 validation tasks
- Multi-language support with full provenance tracking

**Files:**
- `src/librarian/graph_db.py` - Neo4j operations
- `src/librarian/parser.py` - Tree-sitter parsing (~700 lines)
- `src/librarian/graph_constructor.py` - Relationship building
- `src/librarian/retriever.py` - Context retrieval
- `src/librarian/provenance.py` - Metadata tracking

---

### Phase 2: The Reasoner 🧠
**Status:** ✅ Complete ([Details](docs/PHASE2_DOCUMENTATION.md))

**Purpose:** Analyze code dependencies and create prioritized refactoring plans

**Key Components:**
- **Dependency Analyzer** - Identifies impact zones for changes
- **LLM Client** - Integrates with Claude/GPT for reasoning
- **Plan Parser** - Converts LLM output to structured refactor plans
- **Prompt Builder** - Constructs effective analysis prompts
- **Risk Assessment** - Scores changes by complexity and impact

**Deliverables:**
- Dependency graph analysis with impact scoring
- Prioritized refactoring tasks with rationale
- Multi-file change coordination

**Files:**
- `src/reasoner/reasoner.py` - Main orchestration
- `src/reasoner/dependency_analyzer.py` - Dependency tracking
- `src/reasoner/llm_client.py` - LLM integration
- `src/reasoner/plan_parser.py` - Plan extraction

---

### Phase 3: The Compressor 🗜️
**Status:** ✅ Complete ([Bridge](docs/PHASE2_BRIDGE.md))

**Purpose:** Compress context to fit within LLM token limits while preserving critical information

**Key Components:**
- **Jamba 1.5 Mini Integration** - 256k context window for compression
- **Context Validator** - Ensures critical information preserved
- **Hierarchical Compression** - Multi-level context reduction
- **Token Budget Management** - Optimal context allocation

**Deliverables:**
- Up to 90% context compression while preserving semantics
- Configurable compression strategies
- Validation that critical symbols remain

**Files:**
- `src/context_encoder/encoder.py` - Main compression logic
- `src/context_encoder/config.py` - Configuration management
- `src/context_encoder/validator.py` - Validation checks

---

### Phase 4: The Builder 🎨
**Status:** ✅ Complete ([Details](docs/PHASE_4_COMPLETE.md))

**Purpose:** Generate high-quality code using discrete diffusion models

**Key Components:**
- **Discrete Diffusion Model** - Token-level denoising process
- **AST-Aware Masking** - Preserves code structure during generation
- **Multi-Backbone Support** - Works with Mock/GPT/Claude/Gemini
- **Cosine Noise Schedule** - Optimized denoising curve
- **High-Level Orchestrator** - Simplified API for generation

**Deliverables:**
- Discrete diffusion implementation with configurable steps (10/50/100)
- AST-aware masking for structural preservation
- Quality modes: fast (2s), balanced (8s), quality (15s)

**Files:**
- `src/diffusion/diffusion_model.py` - Core diffusion logic (~800 lines)
- `src/diffusion/builder.py` - High-level orchestrator
- `src/diffusion/masking.py` - AST masking utilities
- `src/diffusion/config.py` - Configuration presets

---

### Phase 5: The Integration Loop 🛡️
**Status:** ✅ Complete ([Details](docs/PHASE_5_COMPLETE.md))

**Purpose:** Production-ready safety, user experience, and auditability

**Key Components:**

#### 1. Safety Gate
- **Tree-Sitter Validation** - Parses generated code before disk writes
- **Multi-Language Support** - Python, JavaScript, TypeScript parsers
- **Detailed Error Reports** - Line numbers, error types, context
- **Self-Healing Retry** - Automatic retry with error feedback (up to 3 attempts)

#### 2. Beautiful CLI
- **Typer Framework** - Type-safe command-line interface
- **Rich Terminal Output** - Tables, progress bars, spinners
- **Three Commands:**
  - `refactor` - Generate and apply patches
  - `status` - View run details and provenance
  - `list-runs` - Display recent generation history
- **Risk Scoring** - Auto-apply patches below risk threshold
- **Dry-Run Mode** - Preview changes without modification

#### 3. Complete Provenance
- **Model Usage Tracking** - Which AI models did what
- **Safety Check Logging** - All validation results
- **File Modification Tracking** - SHA256 hashes and diffs
- **JSON Export** - `artifact_metadata_*.json` for every run
- **Timeline Tracking** - Timestamps for each phase

**Deliverables:**
- Zero invalid syntax reaches codebase (safety gate)
- Professional CLI with beautiful output
- Full audit trail for compliance

**Files:**
- `ouroboros_cli.py` - Main CLI entry point (~632 lines)
- `src/utils/syntax_validator.py` - Tree-Sitter validation (~456 lines)
- `src/utils/provenance_logger.py` - Audit logging (~548 lines)
- Enhanced `src/diffusion/builder.py` - Integrated safety gate
- Enhanced `src/ouroboros_pipeline.py` - Provenance integration

---

## 📁 Project Structure

```
ouroboros/
├── 🎯 CLI & Entry Points
│   ├── ouroboros_cli.py              # Main CLI (632 lines)
│   ├── ouroboros.bat                 # Windows launcher
│   └── ouroboros.sh                  # Unix/Linux launcher
│
├── 📚 Documentation
│   ├── README.md                     # This file
│   ├── CHANGELOG.md                  # Version history
│   ├── CONTRIBUTING.md               # Contribution guide
│   ├── LICENSE                       # MIT License
│   └── docs/                         # Detailed documentation
│       ├── index.md                  # Documentation index
│       ├── INSTALLATION.md           # Setup guide
│       ├── CLI_QUICK_REFERENCE.md    # CLI examples
│       ├── PHASE1_COMPLETE.md        # Phase 1 details
│       ├── PHASE2_DOCUMENTATION.md   # Phase 2 details
│       ├── PHASE_4_COMPLETE.md       # Phase 4 details
│       ├── PHASE_5_COMPLETE.md       # Phase 5 details
│       ├── AI21_SETUP.md             # Jamba setup
│       ├── LMSTUDIO_SETUP.md         # LM Studio setup
│       └── GITHUB_SETUP.md           # GitHub guide
│
├── 🧬 Core Pipeline (src/)
│   ├── ouroboros_pipeline.py         # End-to-end orchestration
│   │
│   ├── librarian/                    # Phase 1: Knowledge Graph
│   │   ├── graph_db.py              # Neo4j operations
│   │   ├── parser.py                # Tree-sitter parsing (700 lines)
│   │   ├── graph_constructor.py     # Relationship building
│   │   ├── retriever.py             # Context retrieval
│   │   ├── provenance.py            # Metadata tracking
│   │   └── context_serializer.py    # Context formatting
│   │
│   ├── reasoner/                     # Phase 2: Analysis & Planning
│   │   ├── reasoner.py              # Main orchestrator
│   │   ├── dependency_analyzer.py   # Dependency tracking
│   │   ├── llm_client.py            # LLM integration
│   │   ├── plan_parser.py           # Plan extraction
│   │   ├── prompt_builder.py        # Prompt construction
│   │   └── config.py                # Configuration
│   │
│   ├── context_encoder/              # Phase 3: Compression
│   │   ├── encoder.py               # Jamba integration
│   │   ├── config.py                # Settings
│   │   └── validator.py             # Validation
│   │
│   ├── diffusion/                    # Phase 4: Generation
│   │   ├── builder.py               # High-level orchestrator
│   │   ├── diffusion_model.py       # Discrete diffusion (800 lines)
│   │   ├── masking.py               # AST-aware masking
│   │   └── config.py                # Presets (fast/balanced/quality)
│   │
│   ├── utils/                        # Phase 5: Safety & Utilities
│   │   ├── syntax_validator.py      # 🛡️ Tree-Sitter validation (456 lines)
│   │   ├── provenance_logger.py     # 📊 Audit logging (548 lines)
│   │   └── checksum.py              # File hashing
│   │
│   └── architect/                    # Schema Definitions
│       └── schemas.py               # Data models
│
├── 🔧 Scripts & Tools
│   ├── scripts/
│   │   ├── init_schema.py           # Database initialization
│   │   ├── ingest.py                # Code ingestion
│   │   ├── run_graph_construct.py   # Graph building
│   │   ├── generate_refactor_plan.py
│   │   ├── test_phase2_bridge.py
│   │   └── verify_*.py              # Validation scripts
│   │
│   └── examples/
│       └── example_e2e_generation.py
│
├── 🧪 Tests
│   ├── tests/
│   │   ├── test_*.py                # Unit tests
│   │   ├── synthetic_benchmarks/    # Integration tests
│   │   │   ├── 01_rename_import/
│   │   │   ├── 02_move_function/
│   │   │   ├── 03_change_signature/
│   │   │   └── ... (10 benchmarks)
│   │   └── test_project/            # Test codebase
│   │       ├── auth.py
│   │       ├── userService.ts
│   │       ├── types.ts
│   │       └── app.js
│
├── ⚙️ Configuration
│   ├── requirements.txt             # Python dependencies
│   ├── docker-compose.yml           # Neo4j setup
│   ├── .env.example                 # Environment template
│   ├── .gitignore                   # Git ignore rules
│   └── plan_gemini.json             # Gemini configuration
│
└── 📦 Generated Artifacts (gitignored)
    └── artifacts/
        └── artifact_metadata_*.json  # Provenance logs
```

### Key File Sizes
- `src/librarian/parser.py` - **700 lines** - Multi-language AST extraction
- `src/diffusion/diffusion_model.py` - **800 lines** - Discrete diffusion core
- `ouroboros_cli.py` - **632 lines** - Complete CLI interface
- `src/utils/syntax_validator.py` - **456 lines** - Safety gate validation
- `src/utils/provenance_logger.py` - **548 lines** - Audit logging

---

## 🚀 Usage Examples

### Example 1: Add Caching with Auto-Apply

```bash
python ouroboros_cli.py refactor "Add caching to user lookups" \
  --target src/user_service.py \
  --auto-apply \
  --max-risk 0.3
```

**What happens:**
1. ✅ **Phase 1 (Librarian)**: Analyzes `src/user_service.py` and dependencies via Neo4j graph
2. ✅ **Phase 2 (Reasoner)**: Creates refactor plan with dependency impact analysis
3. ✅ **Phase 3 (Compressor)**: Compresses context with Jamba (if configured, otherwise skipped)
4. ✅ **Phase 4 (Builder)**: Generates code using discrete diffusion (50 steps, ~8s)
5. 🛡️ **Safety Gate**: Validates syntax with Tree-Sitter
   - ✓ If valid → Proceed to step 6
   - ✗ If invalid → Retry with error feedback (up to 3 attempts)
6. ✅ Auto-applies patches with risk ≤ 0.3
7. 💾 Creates backup files (`.backup` extension)
8. 📊 Logs everything to `artifacts/artifact_metadata_*.json`

**Output:**
```
╭─────────── Generation Complete ───────────╮
│ ✓ Task: Add caching to user lookups      │
│ ✓ Duration: 8.5s                         │
│ ✓ Risk Score: 0.25 (Low)                 │
│ ✓ Status: Auto-applied                   │
╰──────────────────────────────────────────╯
```

---

### Example 2: Complex Refactoring with Quality Mode

```bash
python ouroboros_cli.py refactor "Migrate to async/await pattern" \
  --target src/db.py \
  --target src/api.py \
  --config quality \
  --dry-run
```

**What happens:**
1. Analyzes both `src/db.py` and `src/api.py`
2. Uses **quality mode** (100 diffusion steps, ~15s)
3. Shows what would be changed
4. **Does NOT modify files** (dry-run mode)

**Output:**
```
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ File                ┃ Changes   ┃ Risk Score ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ src/db.py           │ +45 -30   │ 0.65       │
│ src/api.py          │ +78 -62   │ 0.72       │
└─────────────────────┴───────────┴────────────┘

⚠️  High risk - Manual review recommended
```

---

### Example 3: Check Run Status and Provenance

```bash
python ouroboros_cli.py status --latest
```

**Output:**
```
╭─────────── Provenance Metadata ───────────╮
│ ✓ Run ID: gen_20250121_123456             │
│ Task: Add caching to user lookups         │
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

            File Modifications            
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
┃ File              ┃ Operation┃ Hash     ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
│ src/user_service  │ update   │ abc123...│
└───────────────────┴──────────┴──────────┘
```

---

### Example 4: List Recent Runs

```bash
python ouroboros_cli.py list-runs --limit 5
```

**Output:**
```
          Recent Generation Runs          
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Run ID             ┃ Task                 ┃ Status  ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ gen_20250121_12345 │ Add caching          │ Success │
│ gen_20250121_12340 │ Add type hints       │ Success │
│ gen_20250121_12335 │ Optimize queries     │ Failed  │
│ gen_20250121_12330 │ Refactor auth        │ Success │
│ gen_20250121_12325 │ Migrate to async     │ Success │
└────────────────────┴──────────────────────┴─────────┘
```

📚 **See [CLI Quick Reference](docs/CLI_QUICK_REFERENCE.md) for 20+ more examples**

---
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

---

## 🔑 Key Features

### 🛡️ Safety Gate - Zero Invalid Code

Every generated code passes through Tree-Sitter validation **before** touching disk:

```python
# Built into the Builder
validator = SyntaxValidator()
result = validator.validate(generated_code, language="python")

if result.is_valid:
    apply_to_disk()
else:
    # Self-healing: retry with error feedback
    retry_with_error_context(result.errors)
```

**Features:**
- ✅ Multi-language support (Python, JavaScript, TypeScript)
- ✅ Detailed error reports (line numbers, error types, context)
- ✅ Self-healing retry loop (up to 3 attempts)
- ✅ Zero invalid syntax reaches your codebase

---

### 🖥️ Beautiful CLI - Professional User Experience

Built with **Typer** and **Rich** for gorgeous terminal output:

```bash
╭─────────── Generation Complete ───────────╮
│ ✓ Task: Add caching to user service      │
│ ✓ Duration: 8.5s                         │
│ ✓ Risk Score: 0.25 (Low)                 │
│ ✓ Status: Auto-applied                   │
╰──────────────────────────────────────────╯

              Models Used              
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Phase     ┃ Model         ┃ Time   ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ reasoner  │ claude-3.5    │ 2500ms │
│ compressor│ jamba-1.5     │ 1200ms │
│ generator │ diffusion     │ 5500ms │
└───────────┴───────────────┴────────┘
```

**Commands:**
- `refactor` - Generate and apply code patches
- `status` - View run details and provenance
- `list-runs` - Display recent generation history

**Options:**
- `--dry-run` - Preview changes without modification
- `--auto-apply` - Automatically apply safe patches
- `--max-risk` - Risk threshold for auto-apply (0.0-1.0)
- `--config` - Quality mode (fast/balanced/quality)

---

### 📊 Complete Provenance - Full Auditability

Every run generates `artifact_metadata_*.json` with:

```json
{
  "run_id": "gen_20250121_123456",
  "task": "Add caching to user service",
  "models_used": [
    {
      "phase": "reasoner",
      "model_name": "claude-3-5-sonnet-20241022",
      "tokens_used": 2500,
      "latency_ms": 2500
    }
  ],
  "safety_checks": [
    {
      "check_type": "syntax_validation",
      "status": "passed",
      "details": "No syntax errors detected"
    }
  ],
  "file_modifications": [
    {
      "file_path": "src/user_service.py",
      "operation": "update",
      "before_hash": "abc123...",
      "after_hash": "def456...",
      "diff": "..."
    }
  ]
}
```

**Tracks:**
- Which AI models did what (Reasoner, Compressor, Generator)
- All safety checks with results
- File modifications with SHA256 hashes
- Complete timing and token usage
- Error logs and retry attempts

---

### ⚡ Smart Generation - Configurable Quality

Three quality modes optimized for different use cases:

| Mode | Steps | Time | Use Case |
|------|-------|------|----------|
| **Fast** | 10 | ~2s | Quick prototyping, simple changes |
| **Balanced** | 50 | ~8s | **Recommended** - Good quality/speed |
| **Quality** | 100 | ~15s | Complex refactorings, production code |

```bash
# Use quality mode for complex changes
python ouroboros_cli.py refactor "Migrate to async/await" \
  --target src/api.py \
  --config quality
```

---

### 🔄 Self-Healing - Automatic Error Recovery

When syntax errors detected:

1. **Extract error details** - Line number, error type, context
2. **Enhance generation prompt** - Add error feedback
3. **Retry generation** - Up to 3 attempts
4. **Log all attempts** - Full provenance trail

```
Attempt 1: Syntax error on line 42 (missing colon)
Attempt 2: ✓ Valid syntax - applying to disk
```

**Result:** Higher success rate, fewer manual interventions

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

📚 **See [CLI Quick Reference](docs/CLI_QUICK_REFERENCE.md) for 20+ more examples**

---

## 🛠️ Advanced Setup

### Option 1: Mock Mode (No External Services)
Perfect for testing without API keys or databases:

```bash
python ouroboros_cli.py refactor "Add caching" \
  --target src/example.py \
  --mock \
  --dry-run
```

**Pros**: No API keys, no database, instant setup  
**Cons**: Generates mock code (not real refactoring)

---

### Option 2: Full Setup (Production)

#### Step 1: Start Neo4j Database
```bash
# Using Docker
docker-compose up -d

# Verify Neo4j running
docker ps

# Access Neo4j Browser
# URL: http://localhost:7474
# User: neo4j
# Password: ouroboros123
```

#### Step 2: Initialize Database Schema
```bash
python scripts/init_schema.py
```

#### Step 3: Ingest Your Codebase
```bash
python scripts/ingest.py \
  --path ./your-project \
  --language python
```

#### Step 4: Configure API Keys

Create `.env` file:
```bash
# Required for Phase 2 (Reasoner)
ANTHROPIC_API_KEY=sk-ant-...
# OR
OPENAI_API_KEY=sk-...

# Optional for Phase 3 (Compressor)
AI21_API_KEY=...
```

#### Step 5: Run Full Pipeline
```bash
python ouroboros_cli.py refactor "Add error handling" \
  --target src/api.py \
  --config balanced
```

📖 **See [Installation Guide](docs/INSTALLATION.md) for detailed setup instructions**

---

## 📊 Technical Details

### Dependencies

**Core Libraries:**
- `neo4j==5.15.0` - Graph database driver
- `tree-sitter==0.20.4` - Multi-language parsing
- `typer==0.9.0` - CLI framework
- `rich==13.7.0` - Terminal formatting
- `anthropic==0.18.0` - Claude integration
- `openai==1.12.0` - GPT integration

**Tree-Sitter Parsers:**
- `tree-sitter-python`
- `tree-sitter-javascript`
- `tree-sitter-typescript`

**Optional:**
- `ai21==2.2.0` - Jamba integration (Phase 3)

Install all dependencies:
```bash
pip install -r requirements.txt
```

---

### Configuration Modes

Create custom configurations in your code:

```python
from src.diffusion.config import DiffusionConfig

# Fast mode - 10 steps
fast_config = DiffusionConfig.fast()

# Balanced mode - 50 steps (default)
balanced_config = DiffusionConfig.balanced()

# Quality mode - 100 steps
quality_config = DiffusionConfig.quality()

# Custom mode
custom_config = DiffusionConfig(
    num_diffusion_steps=75,
    temperature=0.8,
    backbone="claude-3-5-sonnet"
)
```

---

### Graph Schema (Phase 1)

**Node Types:**
- `:File` - Source code files with checksums
- `:Class` - Class definitions with signatures
- `:Function` - Functions/methods with parameters
- `:Variable` - Variable declarations
- `:Import` - Import statements

**Relationship Types:**
- `[:IMPORTS]` - File-to-file dependencies
- `[:INHERITS_FROM]` - Class inheritance
- `[:CALLS]` - Function invocations
- `[:INSTANTIATES]` - Object creation
- `[:CONTAINS]` - Structural containment

**Query Example:**
```cypher
// Find all functions that call a specific function
MATCH (caller:Function)-[:CALLS]->(target:Function {name: 'authenticate'})
RETURN caller.name, caller.file_path
```

---

### Risk Scoring Algorithm

Each patch receives a risk score (0.0-1.0):

```python
risk_score = 0.0

# Syntax validation failure
if not syntax_valid:
    risk_score += 0.5

# Large changes
if lines_changed > 100:
    risk_score += 0.2
elif lines_changed > 50:
    risk_score += 0.1

# Breaking changes
if removes_function or changes_signature:
    risk_score += 0.3

# Touches critical files
if is_critical_file(file_path):
    risk_score += 0.15
```

**Risk Thresholds:**
- `0.0 - 0.3`: Low risk (safe to auto-apply)
- `0.3 - 0.5`: Medium risk (review recommended)
- `0.5 - 1.0`: High risk (manual review required)

---

## 🧪 Testing & Validation

### Run Unit Tests
```bash
# All tests
pytest tests/

# Specific test
pytest tests/test_syntax_validator.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Run Synthetic Benchmarks
```bash
# All 10 benchmarks
pytest tests/synthetic_benchmarks/ -v

# Specific benchmark
pytest tests/synthetic_benchmarks/01_rename_import/ -v
```

### Validate Phase Implementations
```bash
# Validate Phase 1
python scripts/verify_task1.py
python scripts/verify_task2.py
python scripts/verify_task3.py
python scripts/verify_task4.py

# Test Phase 2
python scripts/test_phase2_reasoner.py

# Test Phase 3-4 integration
pytest tests/test_phase2_phase3_integration.py
```

---

## 📚 Documentation

### Quick Links
- 📖 [Installation Guide](docs/INSTALLATION.md) - Complete setup instructions
- 🎯 [CLI Quick Reference](docs/CLI_QUICK_REFERENCE.md) - Command examples
- 📝 [Contributing Guide](CONTRIBUTING.md) - How to contribute
- 📋 [Changelog](CHANGELOG.md) - Version history

### Phase Documentation
- 📘 [Phase 1: The Librarian](docs/PHASE1_COMPLETE.md) - Knowledge graph implementation
- 📗 [Phase 2: The Reasoner](docs/PHASE2_DOCUMENTATION.md) - Analysis and planning
- 📙 [Phase 3: Bridge](docs/PHASE2_BRIDGE.md) - Context compression
- 📕 [Phase 4: The Builder](docs/PHASE_4_COMPLETE.md) - Discrete diffusion
- 📓 [Phase 5: Integration Loop](docs/PHASE_5_COMPLETE.md) - Safety and UX

### Setup Guides
- ⚙️ [AI21 Setup](docs/AI21_SETUP.md) - Jamba configuration
- 🖥️ [LM Studio Setup](docs/LMSTUDIO_SETUP.md) - Local LLM setup
- 🐙 [GitHub Setup](docs/GITHUB_SETUP.md) - Repository configuration

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details

**Author:** Vivek Bendre  
**Version:** 2.0.0  
**Date:** December 21, 2025

---

## 🙏 Acknowledgments

Built with:
- **Neo4j** - Graph database excellence
- **Tree-Sitter** - Robust multi-language parsing
- **Anthropic Claude** - Advanced reasoning capabilities
- **AI21 Jamba** - Long-context compression
- **Typer & Rich** - Beautiful CLI framework

Inspired by:
- Edge, D., et al. (2024). *From Local to Global: A Graph RAG Approach*. arXiv:2404.16130
- Ho, J., et al. (2020). *Denoising Diffusion Probabilistic Models*. NeurIPS 2020

---

## 📧 Contact & Support

- 📖 [Documentation](docs/index.md)
- 🐛 [Issues](https://github.com/your-repo/issues)
- 💬 [Discussions](https://github.com/your-repo/discussions)

---

**Made with ❤️ for the developer community**
