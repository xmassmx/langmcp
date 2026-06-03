## Summary

<!-- What does this change do, and why? -->

## Base branch

Open this PR against **`develop`** (not `main`). Production merges happen via `develop` → `main` when releasing.

## Test plan

- [ ] `uv run ruff check src tests`
- [ ] `uv run pytest tests/unit -v`
- [ ] Updated `CHANGELOG.md` under `## [Unreleased]` if `src/` or `tests/` changed
