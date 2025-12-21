# Contributing to Ouroboros

Thank you for your interest in contributing to Ouroboros! This document provides guidelines for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

## 🤝 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow best practices

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (for Neo4j)
- Git
- Virtual environment (recommended)

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ouroboros.git
   cd ouroboros
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\Activate.ps1
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Neo4j (Optional)**
   ```bash
   docker-compose up -d
   ```

5. **Run Tests**
   ```bash
   pytest tests/
   ```

## 📁 Project Structure

See [README.md](README.md#-project-structure) for the complete project structure.

### Key Directories

- `src/` - Source code organized by phase
- `tests/` - Unit and integration tests
- `docs/` - Documentation
- `scripts/` - Utility scripts
- `examples/` - Example usage

### Module Organization

```
src/
├── librarian/      # Phase 1: Knowledge Graph
├── reasoner/       # Phase 2: Analysis
├── context_encoder/# Phase 3: Compression
├── diffusion/      # Phase 4: Generation
└── utils/          # Phase 5: Safety & Utilities
```

## 🛠️ Making Changes

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test additions/changes

### Coding Standards

1. **Python Style**
   - Follow PEP 8
   - Use type hints
   - Maximum line length: 100 characters
   - Use docstrings for all public functions/classes

2. **Imports**
   ```python
   # Standard library
   import os
   from pathlib import Path
   
   # Third-party
   import typer
   from rich.console import Console
   
   # Local
   from src.utils.syntax_validator import SyntaxValidator
   ```

3. **Documentation**
   - Add docstrings to all public APIs
   - Update README.md if adding new features
   - Create/update docs/ files as needed
   - Include usage examples

4. **Type Hints**
   ```python
   def validate_code(
       code: str,
       language: str = "python"
   ) -> ValidationResult:
       """Validate code syntax."""
       ...
   ```

### File Organization

- One class per file (when appropriate)
- Group related functionality
- Keep files under 500 lines
- Use meaningful names

## 🧪 Testing

### Running Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_syntax_validator.py

# With coverage
pytest --cov=src tests/
```

### Writing Tests

1. **Unit Tests**
   ```python
   def test_syntax_validator_valid_code():
       validator = SyntaxValidator()
       result = validator.validate("print('hello')", "python")
       assert result.is_valid
   ```

2. **Integration Tests**
   - Place in `tests/synthetic_benchmarks/`
   - Test end-to-end workflows
   - Use mock mode when possible

3. **Test Coverage**
   - Aim for >80% coverage
   - Test edge cases
   - Test error conditions

## 📝 Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

### Examples

```bash
feat(cli): add --verbose flag to refactor command

Add verbose logging option to CLI refactor command for debugging.
Includes additional output showing phase transitions.

Closes #123
```

```bash
fix(safety): handle empty validation errors correctly

Fixed crash when validation errors list is empty.
Added guard clause and additional test case.
```

### Best Practices

- Use present tense ("add feature" not "added feature")
- Use imperative mood ("move file" not "moves file")
- First line under 50 characters
- Reference issues when applicable

## 🔄 Pull Request Process

### Before Submitting

1. ✅ Tests pass (`pytest tests/`)
2. ✅ Code follows style guide
3. ✅ Documentation updated
4. ✅ Commits are clean and logical
5. ✅ Branch is up to date with main

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Code follows style guide
- [ ] Self-review completed
```

### Review Process

1. Automated tests run on PR
2. Code review by maintainer
3. Address feedback
4. Merge when approved

## 🐛 Reporting Bugs

### Bug Report Template

```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Run command '...'
2. See error

**Expected behavior**
What should happen

**Environment**
- OS: [e.g., Windows 11]
- Python: [e.g., 3.10.5]
- Ouroboros version: [e.g., 2.0.0]

**Additional context**
Any other relevant information
```

## 💡 Suggesting Features

### Feature Request Template

```markdown
**Feature Description**
Clear description of the feature

**Use Case**
Why is this feature needed?

**Proposed Solution**
How should it work?

**Alternatives**
Other approaches considered
```

## 📚 Documentation

### Types of Documentation

1. **Code Comments**
   - Explain "why" not "what"
   - Use for complex logic

2. **Docstrings**
   - All public functions/classes
   - Parameters, returns, raises
   - Usage examples

3. **README Updates**
   - New features
   - Changed behavior
   - Installation steps

4. **docs/ Files**
   - Architecture changes
   - New phases/components
   - Guides and tutorials

### Documentation Style

- Use Markdown
- Include code examples
- Keep it concise
- Use headings for structure

## 🎯 Development Workflow

### Standard Workflow

1. **Create Issue**
   - Describe problem/feature
   - Get feedback

2. **Create Branch**
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Make Changes**
   - Write code
   - Add tests
   - Update docs

4. **Test Locally**
   ```bash
   pytest tests/
   python ouroboros_cli.py --help
   ```

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(component): add feature"
   ```

6. **Push Branch**
   ```bash
   git push origin feature/my-feature
   ```

7. **Create PR**
   - Fill out template
   - Request review

8. **Address Feedback**
   - Make requested changes
   - Push updates

9. **Merge**
   - Squash and merge
   - Delete branch

## 🔧 Component-Specific Guidelines

### Phase 1: Librarian (Knowledge Graph)
- Use Neo4j best practices
- Add provenance metadata
- Test with synthetic benchmarks

### Phase 2: Reasoner (Analysis)
- Handle multiple LLM providers
- Validate plan schemas
- Test dependency analysis

### Phase 3: Compressor (Context)
- Optimize token usage
- Preserve critical information
- Handle API errors gracefully

### Phase 4: Builder (Generation)
- Maintain AST validity
- Test with various code patterns
- Benchmark performance

### Phase 5: Integration (Safety)
- Validate all inputs
- Log all operations
- Test error conditions

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Recognized in documentation

## 📧 Contact

- Issues: GitHub Issues
- Discussions: GitHub Discussions
- Email: [project email]

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Ouroboros! 🐍
