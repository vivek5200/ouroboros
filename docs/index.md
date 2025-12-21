---
layout: home
title: Home
nav_order: 1
---

# Ouroboros
{: .fs-9 }

**AI-powered code refactoring with discrete diffusion**
{: .fs-6 .fw-300 }

[Get Started](./INSTALLATION){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 } [CLI Reference](./CLI_QUICK_REFERENCE){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 } [View on GitHub](https://github.com/vivek5200/ouroboros){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## Project Overview

Ouroboros is a production-ready AI code generation system that combines GraphRAG for infinite context, discrete diffusion for high-quality code generation, and comprehensive safety gates with complete provenance logging.

### Key Features

* **🛡️ Safety Gates**: Tree-Sitter syntax validation prevents invalid code
* **🔄 Self-Healing**: Automatic retry loops with error feedback
* **🧠 Discrete Diffusion**: High-quality code generation (Phase 4)
* **📊 Complete Provenance**: Full audit trail for every run
* **🖥️ Beautiful CLI**: Rich terminal interface with Typer
* **⚡ GraphRAG Context**: Neo4j knowledge graph for deterministic retrieval

### All Phases Complete ✅

| Phase | Status | Description |
|:------|:-------|:------------|
| **Phase 1** | ✅ Complete | The Librarian - Knowledge Graph (Neo4j + Tree-sitter) |
| **Phase 2** | ✅ Complete | The Reasoner - Dependency Analysis & Planning |
| **Phase 3** | ✅ Complete | The Compressor - Context Encoding (Jamba 256k) |
| **Phase 4** | ✅ Complete | The Builder - Discrete Diffusion Code Generation |
| **Phase 5** | ✅ Complete | Integration Loop - Safety, CLI, Provenance |

---

### Quick Start

```bash
# Install
pip install -r requirements.txt

# Refactor code (mock mode)
python ouroboros_cli.py refactor "Add caching" \
  --target src/user_service.py \
  --mock \
  --dry-run

# Check status
python ouroboros_cli.py status --latest
```