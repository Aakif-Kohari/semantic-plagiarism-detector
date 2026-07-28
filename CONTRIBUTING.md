# 🤝 Contributing to Semantic Plagiarism Detection System

First of all, thank you for your interest in contributing! 🎉

Whether you're fixing a bug, improving documentation, adding a feature, or suggesting an idea, your contribution is greatly appreciated.

Please read this guide before getting started.

---

# 📌 Contribution Workflow

Every contribution should follow this workflow:

```text
Discussion (Optional)
        ↓
Issue Assignment
        ↓
Implementation Plan (if requested)
        ↓
Development
        ↓
Pull Request
        ↓
Code Review
        ↓
Merge
```

> **Please do not start working on an issue unless it has been assigned to you or approved by a maintainer.**

---

# 🚀 Getting Started

## 1. Fork the repository

Fork this repository to your GitHub account.

## 2. Clone your fork

```bash
git clone https://github.com/<your-username>/<repo-name>.git
```

## 3. Create a new branch

```bash
git checkout -b feature/your-feature-name
```

## 4. Install dependencies

```bash
pip install -r requirements.txt
pip install pytest-cov
```

## 5. Run the project

Ensure the project builds and runs correctly before making any changes.

### 💡 Testing with Pre-populated Seed Data

Instead of manually registering admin accounts and uploading test documents to verify dashboard visual styles or logic behavior, you can load pre-populated seed data:

```bash
make load-seed   # Or: python scripts/manage_seed.py load
```
This loads pre-configured accounts:
* **Admin**: `admin` / `admin123`
* **Teacher**: `teacher` / `teacher123`


### Running Tests and Coverage

To run tests with coverage reporting:
```bash
pytest --cov=src --cov-report=term-missing
```
The test suite enforces an 80% minimum coverage threshold.

---

# 📋 Before You Start

Before requesting an issue:

- Read the issue description carefully.
- Ask questions if anything is unclear.
- Wait for maintainer approval before beginning work.
- Work on **one assigned issue at a time** unless approved otherwise.
- Search existing Issues and Discussions before opening a new one.

---

# 📝 Contribution Guidelines

Please follow these guidelines when contributing:

- Keep code clean, readable, and modular.
- Follow the existing project architecture.
- Write meaningful commit messages.
- Add comments and docstrings where appropriate.
- Test your implementation before opening a Pull Request.
- Avoid unrelated code changes within the same PR.

### Project Structure

- Core NLP algorithms, parsers, embeddings, indexing, and similarity modules belong in:

```
src/core/
```

- Database managers and persistence utilities belong in:

```
src/db/
```

- Visualization and plotting components belong in:

```
src/visualization/
```

- Unit tests should be added to the corresponding directory inside:

```
tests/
```

Example:

```
src/core/parser.py
tests/core/test_parser.py
```

---

# 📌 Issue Assignment Policy

Issues are assigned on a first-come, first-served basis unless stated otherwise.

For larger or more complex features, maintainers may request a short implementation plan before assigning the issue.

Once assigned:

- Provide a meaningful progress update every **2–3 days**.
- If there is no communication or visible progress, the issue may be reassigned.
- If you need more time, simply leave a comment.

Please do **not** submit Pull Requests for unassigned issues unless a maintainer has approved it beforehand.

---

# 🔀 Pull Request Guidelines

Before opening a Pull Request:

- Sync with the latest `main`
- Test your changes locally
- Ensure your code builds successfully
- Add or update tests where applicable
- Update documentation if needed

Every Pull Request **must** include:

## Description

Briefly explain:

- What changed
- Why it changed
- How it was tested

Example:

```
src/core/parser.py
- Added OCR preprocessing support

src/db/database.py
- Added SQLite persistence layer
```

---

## Related Issue

Every PR **must** reference its issue using:

```text
Fixes #<issue_number>
```

---

## Checklist

- [ ] Code builds successfully
- [ ] Tests pass
- [ ] Documentation updated (if applicable)
- [ ] No unnecessary dependencies introduced
- [ ] No breaking changes
- [ ] Issue linked using `Fixes #...`

---

## Screenshots / Test Results (Optional)

If applicable, include:

- Screenshots
- Test results
- Benchmark results
- Coverage reports

Example:

```
Tests: 42 passed
Coverage: 87%
Performance: ~20% faster than previous implementation
```

---

# 💬 Communication

Open communication helps everyone.

If you:

- need clarification,
- get stuck,
- cannot continue,
- or wish to stop working on an issue,

please leave a comment on the issue instead of disappearing.

Maintainers appreciate communication far more than silence.

---

# 🤖 AI-Assisted Contributions

AI tools such as ChatGPT, GitHub Copilot, Claude, or Gemini may be used as productivity aids.

However:

- You must understand every line of code you submit.
- Review and test AI-generated code thoroughly.
- Be prepared to explain your implementation during code review.
- Do not submit untested or blindly generated code.

---

# 🧪 Code Style

Please follow these conventions:

- Follow **PEP 8**
- Use descriptive variable and function names
- Keep functions small and modular
- Write reusable code where possible
- Avoid unnecessary dependencies
- Keep imports organized

---

# ⏳ Review Process

Maintainers aim to:

- Respond to issue assignment requests within **24 hours**
- Review Pull Requests within **24–48 hours**
- Provide constructive feedback as quickly as possible

Response times may vary depending on maintainer availability.

---

# ❌ Pull Requests May Be Closed If

A Pull Request may be closed if:

- It addresses an unassigned issue without approval
- It does not follow this contribution guide
- It remains inactive without communication
- Requested review changes are ignored for an extended period
- It introduces unnecessary complexity or unrelated changes

Closed Pull Requests are welcome to be improved and resubmitted.

---

# ❤️ Thank You

Every contribution—whether it's code, documentation, bug reports, feature ideas, or discussions—helps improve this project.

Thank you for taking the time to contribute!
