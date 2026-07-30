# Contributing

## Welcome

Thank you for your interest in contributing to the Semantic Plagiarism Detection System! We welcome contributions from everyone, whether you're fixing a bug, improving documentation, adding a feature, or suggesting an idea.

## Getting Started

### Fork the repository

Fork this repository to your GitHub account using the "Fork" button on the repository page.

### Clone locally

```bash
git clone https://github.com/<your-username>/semantic-plagiarism-detector.git
cd semantic-plagiarism-detector
```

### Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the project

```bash
streamlit run app/streamlit_app.py
```

The application will open at http://localhost:8501. Default credentials are username `admin` and password `admin123`.

## Branching Strategy

Use descriptive branch names following these patterns:

- `feature/add-search` - For new features
- `fix/login-bug` - For bug fixes
- `docs/update-contributing` - For documentation changes
- `refactor/embedding-model` - For code refactoring

## Code Style

This project uses **Ruff** for linting and formatting:

- **Check code style**: `ruff check .`
- **Format code**: `ruff format .`

Follow PEP 8 conventions and keep code clean, readable, and modular.

## Running Tests

Run the test suite using pytest:

```bash
python -m pytest
```

The project uses pytest with configuration in `pytest.ini`. Tests are located in the `tests/` directory and mirror the structure of the `src/` directory.

## Submitting Pull Requests

- Keep PRs focused on a single issue or feature
- Write meaningful commit messages that explain "why" not just "what"
- Link related issues using "Fixes #issue_number" in your PR description
- Ensure all tests pass before submitting
- Run `ruff check .` and `ruff format .` to maintain code quality
- Respond to review feedback promptly and make requested changes

## Reporting Issues

When opening bug reports or feature requests:

- Search existing issues first to avoid duplicates
- Use the provided issue templates in `.github/ISSUE_TEMPLATE/`
- Provide clear steps to reproduce bugs
- Include relevant error messages, logs, or screenshots
- Describe the expected behavior versus actual behavior
