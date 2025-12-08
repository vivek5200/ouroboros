# 🐍 Ouroboros - Phase 1: The Librarian

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Neo4j 5.15](https://img.shields.io/badge/neo4j-5.15-brightgreen.svg)](https://neo4j.com/)

**Version:** 1.0.0  
**Date:** December 08, 2025  
**Author:** Vivek Bendre

## Overview

Implementation of the GraphRAG-based structural memory system for the Ouroboros autonomous software engineering architecture. This phase builds the foundational "Librarian" component that provides infinite, deterministic context retrieval using graph traversal instead of semantic similarity.

## Architecture Components

### Phase 1: The Librarian (Memory Layer)
- ✅ Neo4j Graph Database with provenance schema
- ✅ Ingestion pipeline with file checksum tracking
- ✅ Graph construction for structural dependencies
- ✅ Synthetic test suite for validation

## Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Git

### 2. Setup Neo4j

```powershell
# Start Neo4j container
docker-compose up -d

# Verify Neo4j is running
docker ps
```

Access Neo4j Browser at: http://localhost:7474  
Login: `neo4j` / `ouroboros123`

### 3. Install Python Dependencies

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 4. Initialize Database Schema

```powershell
python scripts/init_schema.py
```

## Project Structure

```
ouroboros/
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

## Provenance Schema

Every node in the graph contains:
- `model_name`: Component that created the node
- `model_version`: Version of the component
- `prompt_id`: Unique identifier for the operation
- `timestamp`: ISO 8601 creation time
- `context_checksum`: SHA256 hash of source content

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
