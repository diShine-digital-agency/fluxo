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
# macOS / Windows (with display)
pytest

# Linux / headless CI
QT_QPA_PLATFORM=offscreen pytest
```

> **Note:** On Linux you may need `libegl1` installed for the offscreen Qt platform.

### Linting

Fluxo uses [Ruff](https://docs.astral.sh/ruff/) for linting and import sorting:

```bash
pip install ruff
ruff check src/ tests/
ruff format --check src/ tests/
```

### Code Style

- Follow PEP 8
- Use type hints on all public APIs
- Maximum line length: 100 characters (configured in `pyproject.toml`)
- Use docstrings for public classes and functions
- Use `from __future__ import annotations` for modern type syntax
- UI code must use **PySide6** (not PyQt6)

## Project Layout

```
src/fluxo/
├── models/          # Typed data models
├── parsers/         # M3U and XMLTV parsers
├── services/        # Business logic layer
├── server/          # Local HTTP playlist server
├── ui/              # PySide6 widgets and dialogs
├── persistence/     # Settings and autosave
├── app.py           # Entry point
└── __main__.py      # Module entry point
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass: `pytest`
4. Run the linter: `ruff check src/ tests/`
5. Update CHANGELOG.md
6. Submit the pull request

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
