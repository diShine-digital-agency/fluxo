# Contributing to Fluxo

Thank you for your interest in contributing to Fluxo! This document provides guidelines for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/fluxo.git`
3. Create a virtual environment: `python -m venv .venv`
4. Activate it: `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows)
5. Install dependencies: `pip install -e ".[dev]"`
6. Create a branch: `git checkout -b feature/your-feature`

## Development

### Running the App

```bash
python -m fluxo
```

### Running Tests

```bash
pytest
```

### Code Style

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for public APIs

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Submit the pull request

## Reporting Issues

Use GitHub Issues with the provided templates. Include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- System information (OS, Python version)

## Legal

By contributing, you agree that your contributions will be licensed under the MIT License.
Fluxo is a neutral playlist-management tool. Do not submit contributions that bundle
copyrighted streams or facilitate piracy.
