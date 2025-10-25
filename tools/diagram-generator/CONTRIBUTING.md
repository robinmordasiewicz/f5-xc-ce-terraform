# Contributing to Azure + F5 XC Diagram Generator

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment for all contributors

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Terraform (for testing)
- Azure CLI (for local development)

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/f5-xc-ce-terraform.git
   cd f5-xc-ce-terraform/tools/diagram-generator
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

## Development Workflow

### Branch Strategy

- `main` - Stable, production-ready code
- `develop` - Integration branch for features
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches
- `hotfix/*` - Urgent production fixes

### Making Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Write clear, self-documenting code
   - Follow existing code style and patterns
   - Add type hints to all functions
   - Update docstrings for any modified functions

3. **Write tests:**
   ```bash
   # Create test file in tests/
   # Follow naming convention: test_<module>.py
   pytest tests/test_your_module.py -v
   ```

4. **Run code quality checks:**
   ```bash
   # Format code
   black src/ tests/
   isort src/ tests/

   # Lint code
   ruff check src/ tests/

   # Type check
   mypy src/

   # Run all tests
   pytest --cov=diagram_generator
   ```

5. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add awesome new feature"
   ```

   **Commit Message Format:**
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `test:` - Test additions/changes
   - `refactor:` - Code refactoring
   - `chore:` - Maintenance tasks
   - `perf:` - Performance improvements

6. **Push and create pull request:**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style Guidelines

### Python Style

- **PEP 8 compliance** - Follow Python style guide
- **Line length:** 100 characters maximum
- **Type hints:** Use for all function parameters and returns
- **Docstrings:** Google-style docstrings for all public functions

### Example Function

```python
def process_resources(
    resources: List[TerraformResource],
    filter_type: Optional[str] = None,
) -> List[TerraformResource]:
    """
    Process and filter Terraform resources.

    Args:
        resources: List of Terraform resources to process
        filter_type: Optional resource type to filter by

    Returns:
        Filtered list of Terraform resources

    Raises:
        ValueError: If filter_type is invalid
    """
    # Implementation
    pass
```

### Code Organization

- **Imports:** Group by standard library, third-party, local
- **Constants:** UPPER_CASE at module level
- **Classes:** PascalCase
- **Functions:** snake_case
- **Private methods:** Prefix with `_`

## Testing Guidelines

### Test Structure

```python
def test_feature_success():
    """Test successful feature execution."""
    # Arrange
    collector = TerraformCollector()

    # Act
    result = collector.collect_resources()

    # Assert
    assert len(result) > 0
```

### Test Categories

1. **Unit Tests** - Test individual functions/methods
2. **Integration Tests** - Test component interactions
3. **Mock External Services** - Don't make real API calls in tests

### Coverage Requirements

- **Minimum:** 80% code coverage
- **Target:** 90% code coverage
- **Run coverage:**
  ```bash
  pytest --cov=diagram_generator --cov-report=html
  open htmlcov/index.html
  ```

## Documentation

### Adding Documentation

- **README.md** - Update for user-facing changes
- **Docstrings** - Keep inline documentation current
- **Type hints** - Self-documenting code
- **Examples** - Add examples for new features

### Documentation Style

- Clear and concise
- Include code examples
- Explain the "why" not just the "what"
- Keep it updated with code changes

## Pull Request Process

### Before Submitting

- [ ] All tests pass
- [ ] Code is formatted and linted
- [ ] Type checking passes
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] Branch is up to date with develop

### PR Checklist

Your PR description should include:

- **Description:** What does this PR do?
- **Motivation:** Why is this change needed?
- **Testing:** How was this tested?
- **Related Issues:** Closes #123

### Review Process

1. **Automated Checks:** CI/CD must pass
2. **Code Review:** At least one approval required
3. **Testing:** Verify tests cover changes
4. **Documentation:** Check docs are updated

## Project Structure

```
diagram-generator/
├── src/diagram_generator/     # Source code
│   ├── __init__.py
│   ├── cli.py                 # CLI entry point
│   ├── models.py              # Data models
│   ├── exceptions.py          # Custom exceptions
│   ├── utils.py               # Utilities
│   ├── *_collector.py         # Data collectors
│   ├── correlation.py         # Correlation engine
│   └── lucid_*.py             # Lucidchart integration
├── tests/                     # Test suite
│   ├── conftest.py            # pytest fixtures
│   └── test_*.py              # Test modules
├── pyproject.toml             # Project configuration
├── .pre-commit-config.yaml    # Pre-commit hooks
└── README.md                  # User documentation
```

## Adding New Features

### New Data Collector

1. Create `src/diagram_generator/new_collector.py`
2. Implement collector class with type hints
3. Add Pydantic models in `models.py`
4. Create tests in `tests/test_new_collector.py`
5. Update CLI to integrate new collector
6. Update README with new feature

### New Correlation Method

1. Add method to `ResourceCorrelator` class
2. Add relationship type to `RelationshipType` enum
3. Write comprehensive tests
4. Update documentation

## Troubleshooting

### Common Issues

**Import errors:**
```bash
pip install -e ".[dev]"
```

**Pre-commit hooks failing:**
```bash
pre-commit run --all-files
```

**Tests failing:**
```bash
pytest -v --tb=short
```

## Getting Help

- **GitHub Issues:** Report bugs or request features
- **GitHub Discussions:** Ask questions or discuss ideas
- **Pull Requests:** Propose code changes

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release branch
4. Tag release: `git tag v0.1.0`
5. Push tag: `git push origin v0.1.0`
6. GitHub Actions handles publishing

## License

By contributing, you agree that your contributions will be licensed under the project's license.

## Thank You!

Your contributions make this project better for everyone. Thank you for taking the time to contribute!
