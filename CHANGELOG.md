# Changelog

All notable changes to the **Semantic Plagiarism Detection System** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 24-hour Redis caching for generated PNG and PDF originality badges and certificates based on student ID and date (`src/utils/badge_generator.py`, `src/utils/redis_cache.py`).
- Automated fault tolerance test for mid-session Redis connection drop and graceful in-memory failover (`tests/core/test_fault_tolerance.py`, `tests/utils/test_redis_fallback_failover.py`).
- Added `--recursive` support to the CLI scan command for scanning documents in nested subdirectories.

### Fixed
- Robust claim parsing in `.github/workflows/ecsoc-automation.yml` using structured hidden HTML comments to prevent breaking on greeting message variations.

### Changed
- Optimized `clear_session` and `clear_pattern` with Redis pipelining to batch deletions into a single network round-trip (`src/utils/redis_cache.py`).
- Warning list pagination no longer writes `st.session_state` directly; page updates are applied via a view-layer callback (`src/utils/warning_list.py`).

## [1.0.0] - 2026-07-21

### Added
- Cross-lingual preprocessing pipeline supporting language detection and automatic English alignment (`src/core/cross_lingual.py`, `src/core/translator.py`).
- SQLite-backed corpus database and chunk vector persistence (`src/db/corpus_db.py`).
- Plagiarism incident tracking and review status management (`src/db/incidents.py`).
- PDF report export utility (`src/utils/pdf_report.py`).
- Webhook alert integration for high-similarity matches (`src/core/webhook.py`).
- RoBERTa-based AI-generated text detection module (`src/core/ai_detector.py`).
- Redis caching utility for multi-node deployments (`src/utils/redis_cache.py`).
- Originality certificate generator (`src/utils/badge_generator.py`).
- Daily summary email notification service (`src/utils/daily_summary_email.py`).
- Standard open-source governance documents (`CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, `CHANGELOG.md`, GitHub issue templates).

### Changed
- Reorganized `tests/` directory structure into modular `tests/app/`, `tests/core/`, `tests/db/`, `tests/utils/`, and `tests/visualization/`.
- Moved `warning_list.py` into `src/utils/` to maintain strict `src/` modular encapsulation.
- Updated `requirements.txt` to remove duplicate dependency entries.

### Fixed
- Handled missing `redis` dependency in `src/utils/redis_cache.py` to prevent import crashes during test collection.
- Removed legacy duplicate `utils/pdf_report.py` file to ensure tests validate the production PDF report module.
