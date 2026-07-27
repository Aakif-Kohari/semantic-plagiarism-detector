# CI/CD Guide

This document describes the GitHub Actions workflows used in this repository, the events that trigger them, the permissions and secrets they rely on, and the standard deployment steps for running the application.

---

## 1. Workflows

### 1.1 CI Pipeline

File: [.github/workflows/ci.yml](../.github/workflows/ci.yml)

Purpose:
- Runs the main validation pipeline for the application.
- Installs dependencies, runs Ruff, and executes the test suite with coverage enforcement.

Trigger:
- `push` to `main`
- `pull_request` targeting `main`

Job summary:
- `test-and-lint`
  - Runs on `ubuntu-latest`
  - Uses Python `3.11`
  - Installs project dependencies from `requirements.txt`
  - Installs `pytest`, `pytest-cov`, and `ruff`
  - Runs `ruff check .`
  - Runs `python scripts/run_tests.py --all --enforce-coverage 85`

Notes:
- This workflow is the primary gate for merge quality on `main`.
- Coverage is enforced at `85%`.

---

### 1.2 Lint

File: [.github/workflows/lint.yml](../.github/workflows/lint.yml)

Purpose:
- Runs a dedicated linting workflow on pull requests.
- Checks both Ruff and the custom Pylint rule set for Streamlit anti-patterns.

Trigger:
- `pull_request` targeting `main` or `master`

Job summary:
- `ruff`
  - Runs on `ubuntu-latest`
  - Uses Python `3.10`
  - Installs `ruff` and `pylint`
  - Runs `ruff check .`
  - Runs `pylint --load-plugins=pylint_plugins.streamlit_lint --disable=all --enable=streamlit-global-mutation app/ src/`

Notes:
- This workflow is separate from the main CI pipeline so lint regressions are visible early on pull requests.

---

### 1.3 ECSoC Automation

File: [.github/workflows/ecsoc-automation.yml](../.github/workflows/ecsoc-automation.yml)

Purpose:
- Automates issue and pull request triage for the ECSoC'26 contribution flow.
- Assigns contributors, adds labels, posts welcome comments, and cleans up stale claims.

Triggers:
- `issue_comment` with `created`
- `pull_request_target` with `opened`
- `schedule` at `0 0 * * *` UTC
- `workflow_dispatch`

Permissions:
- `issues: write`
- `pull-requests: write`

Job summary:
- `issue-claim`
  - Runs on issue comments.
  - Ignores PR comments.
  - Assigns the commenter to the issue when possible.
  - Adds the `ECSoC26` label.
  - Enforces a maximum of 5 open claimed issues per contributor.

- `pr-automation`
  - Runs when a pull request is opened via `pull_request_target`.
  - Attempts to assign the PR author.
  - Adds the `ECSoC26` label.
  - Posts a welcome comment.

- `auto-unassign-stale`
  - Runs on schedule and on manual dispatch.
  - Removes excess claims above 5 open issues.
  - Removes inactive claims older than 4 days.
  - Removes the `ECSoC26` label when an issue is released back to the pool.

Security note:
- `pull_request_target` is used intentionally for repository-level triage actions.
- The workflow does not check out or execute contributor code.

---

## 2. Secrets and Permissions

### Required secrets

The current workflows do not require any repository secrets.

### Built-in GitHub token usage

All automation uses the default `GITHUB_TOKEN` provided by GitHub Actions through `actions/github-script`.

### Permission requirements

The ECSoC automation workflow needs write access to:
- Issues
- Pull requests

If repository or organization settings restrict workflow permissions, make sure the default workflow token can write to issues and pull requests.

### Optional secrets for application deployment

These are not required for the workflows above, but may be needed if you run the application with external integrations:
- `PLAGIARISM_WEBHOOK_URL`
- `APP_BASE_URL`
- `SMTP_SERVER`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `REDIS_URL`
- `API_BEARER_TOKEN`

---

## 3. Local Prerequisites for CI Parity

To match the CI environment locally, install:
- Python `3.11` for the main CI path
- Python `3.10` if you want to mirror the lint job exactly
- `pytest`
- `pytest-cov`
- `ruff`
- `pylint`

Recommended local checks:

```bash
ruff check .
python scripts/run_tests.py --all --enforce-coverage 85
```

---

## 4. Deployment Steps

This repository does not currently include an automated production deployment workflow in GitHub Actions. Deployment is performed using the application runtime defined in the repo.

### 4.1 Docker deployment

Use Docker Compose for a reproducible local or server deployment:

```bash
docker compose up --build
```

This starts the Streamlit application and any optional services defined in [docker-compose.yml](../docker-compose.yml).

To rebuild after dependency changes:

```bash
docker compose build --no-cache
docker compose up
```

To stop the stack:

```bash
docker compose down
```

### 4.2 Direct Streamlit deployment

For a simple local run:

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

### 4.3 API deployment

If you expose the FastAPI service separately, start it with:

```bash
uvicorn src.api.app:app --reload --port 8000
```

### 4.4 Environment configuration

Set any required runtime values before deployment. Common variables include:
- `PLAGIARISM_WEBHOOK_URL`
- `APP_BASE_URL`
- `SMTP_SERVER`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `REDIS_URL`
- `API_BEARER_TOKEN`

Use a `.env` file for local development or configure variables in your deployment platform.

---

## 5. Maintenance Checklist

Before merging CI/CD-related changes:
- Confirm the workflow trigger branches are still correct.
- Confirm Python versions match the intended support matrix.
- Confirm any new secrets are documented.
- Confirm the workflow token permissions are sufficient.
- Run `ruff check .` and the relevant tests locally.
