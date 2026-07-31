# Development Guide

This document explains how to set up the local development environment and use the project's pre-commit hooks.

## Pre-commit Hooks

This project uses **pre-commit** to automatically run formatting, linting, and basic validation checks before each commit.

### Install pre-commit

```bash
pip install pre-commit
```

### Install Git hooks

```bash
pre-commit install
```

### Run hooks manually

To run all configured hooks on every file:

```bash
pre-commit run --all-files
```

To run the hooks only on staged files:

```bash
pre-commit run
```

## Configured Hooks

The project currently runs the following hooks:

* Ruff (Python linting with automatic fixes)
* Black (Python code formatting)
* isort (Import sorting)
* Trailing Whitespace
* End-of-File Fixer
* YAML Validation
* Large File Check

These checks help maintain consistent code quality and reduce formatting and linting issues before code reaches CI.
