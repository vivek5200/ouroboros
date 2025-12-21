# Changelog

All notable changes to Ouroboros will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-12-21

### Added - Phase 5: The Integration Loop 🎉

#### Safety Gate
- Tree-Sitter syntax validator for Python, JavaScript, TypeScript
- Automatic syntax validation before any code touches disk
- Detailed error reporting with line numbers and context
- Self-healing retry loop (up to 3 attempts with error feedback)
- Configurable safety gate enable/disable

#### CLI
- Beautiful CLI using Typer and Rich libraries
- `refactor` command - Generate and apply code patches
- `status` command - Check run status and provenance
- `list-runs` command - View recent generation runs
- Progress bars and spinners for long operations
- Rich table output for results
- Dry-run mode to preview changes
- Auto-apply for low-risk patches
- Risk scoring (0.0-1.0) for all patches
- Windows (`ouroboros.bat`) and Unix (`ouroboros.sh`) launchers

#### Provenance Logging
- Complete audit trail for every generation run
- Model usage tracking (Reasoner, Compressor, Generator)
- Safety check logging with timestamps
- File modification tracking with SHA256 hashes
- JSON export to `artifact_metadata.json`
- Metadata includes: run_id, models_used, safety_checks, file_modifications

#### Builder Enhancements
- Integrated syntax validator into generation pipeline
- Retry mechanism with enhanced error feedback
- Validation result tracking in metadata
- Configurable max retry attempts

#### Pipeline Integration
- Provenance logger initialized for every run
- Model usage tracked across all phases
- Safety checks logged after generation
- File modifications tracked on apply
- Error logging with failure provenance

#### Documentation
- `PHASE_5_COMPLETE.md` - Comprehensive Phase 5 guide
- `CLI_QUICK_REFERENCE.md` - Quick CLI reference
- `PHASE_5_SUMMARY.md` - Implementation summary
- Updated main `README.md` with Phase 5 info
- `CONTRIBUTING.md` - Contribution guidelines
- `CHANGELOG.md` - This file

#### Dependencies
- Added `typer>=0.9.0` for CLI framework
- Added `rich>=13.7.0` for beautiful terminal output
- Added `click>=8.1.0` as typer dependency

### Changed
- Updated `.gitignore` to ignore test files and artifacts
- Moved all documentation to `docs/` folder
- Updated `README.md` with new project structure
- Enhanced error handling across all components

### Fixed
- Builder now validates syntax before applying changes
- Proper error context in validation failures
- Provenance saved even on generation failures

## [1.5.0] - 2025-12-10

### Added - Phase 4: The Builder

#### Discrete Diffusion
- Discrete diffusion model for code generation
- Cosine noise schedule (1000 steps)
- Classifier-free guidance (CFG scale 7.5)
- Temperature control for generation
- Multiple backbone support (Mock, GPT, Claude)

#### Builder Component
- High-level orchestrator for code generation
- Batch patch generation
- Risk scoring for patches
- Unified diff generation
- Provenance metadata tracking

#### AST Masking
- Tree-sitter based AST masking
- Target-specific function/class masking
- Masked span tracking
- Multi-language support

#### Configuration
- Fast mode (10 steps)
- Balanced mode (50 steps)
- Quality mode (100 steps)
- Mock mode for testing

#### Documentation
- `PHASE_4_COMPLETE.md` - Complete Phase 4 documentation
- Architecture diagrams
- Usage examples
- API reference

### Changed
- Refactored generation pipeline
- Enhanced metadata tracking
- Improved error handling

## [1.0.0] - 2025-12-08

### Added - Phase 1: The Librarian

#### Knowledge Graph
- Neo4j graph database integration
- Tree-sitter code parsing (Python, JS, TS)
- Provenance metadata tracking
- Code checksum validation

#### Graph Construction
- File node creation
- Function/class node extraction
- Dependency relationship mapping
- Import tracking

#### Retrieval
- Graph traversal queries
- Context extraction
- Related node discovery

#### Infrastructure
- Docker Compose setup for Neo4j
- Database schema initialization
- Ingestion pipeline
- Synthetic benchmarks

### Added - Phase 2: The Reasoner

#### Dependency Analysis
- Code dependency tracking
- Impact assessment
- Change propagation analysis

#### LLM Integration
- Claude 3.5 Sonnet support
- GPT-4 support
- Anthropic API client
- Plan generation

### Added - Phase 3: The Compressor

#### Context Encoding
- AI21 Jamba 1.5 Mini integration
- 256k token context window
- Context compression
- Token optimization

#### Configuration
- AI21 API setup
- Compression parameters
- Validation pipeline

### Infrastructure
- Python 3.10+ support
- Virtual environment setup
- Requirements management
- Environment variables (.env)

## [Unreleased]

### Planned Features
- Semantic validation (beyond syntax)
- Security scanning
- Performance profiling
- Web UI
- VS Code extension
- GitHub Actions integration
- CI/CD pipeline
- Additional language support
- Improved retry strategies
- Rollback automation

---

## Version History

- **v2.0.0** (Dec 21, 2025) - Phase 5: Integration Loop (Safety, CLI, Provenance)
- **v1.5.0** (Dec 10, 2025) - Phase 4: The Builder (Discrete Diffusion)
- **v1.0.0** (Dec 08, 2025) - Phase 1-3: Foundation (Graph, Reasoner, Compressor)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
