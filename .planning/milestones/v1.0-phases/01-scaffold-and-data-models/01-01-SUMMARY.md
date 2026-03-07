---
phase: 01-scaffold-and-data-models
plan: "01"
subsystem: infra
tags: [uv, pyproject, ruff, mypy, pytest, pre-commit, src-layout, python]

# Dependency graph
requires: []
provides:
  - uv-managed src-layout Python project with pyproject.toml
  - alteryx_diff package importable from .venv via editable install
  - ruff lint/format config (88-char line, py311 target, E/F/I/UP/B/SIM rules)
  - mypy strict mode config with tests.* override
  - pytest config with importlib mode and tests/ testpath
  - pre-commit hooks: ruff-check, ruff-format, mypy (src/ only), pre-commit-hooks
  - uv.lock for reproducible installs
  - py.typed PEP 561 marker declaring typed package
  - models/ sub-package placeholder for Plan 02 to populate
affects: [02-data-models, all-subsequent-phases]

# Tech tracking
tech-stack:
  added:
    - uv 0.8.12 (project/venv manager)
    - uv_build>=0.10.7,<0.11.0 (build backend)
    - lxml>=5.0 (runtime dep, installed 6.0.2)
    - networkx>=3.6 (runtime dep, installed 3.6.1)
    - pytest>=8.0 (dev dep, installed 9.0.2)
    - mypy>=1.15 (dev dep, installed 1.19.1)
    - ruff>=0.15 (dev dep, installed 0.15.4)
    - pre-commit>=3.0 (dev dep, installed 4.5.1)
  patterns:
    - src-layout (src/alteryx_diff/) prevents accidental root imports
    - pyproject.toml as single config file for all tools (ruff, mypy, pytest)
    - uv.lock committed for exact reproducible installs
    - pre-commit mypy hook restricted to src/ only (files: ^src/) to avoid isolated-env import errors on tests/

key-files:
  created:
    - pyproject.toml
    - .pre-commit-config.yaml
    - .python-version
    - README.md
    - uv.lock
    - src/alteryx_diff/__init__.py
    - src/alteryx_diff/py.typed
    - src/alteryx_diff/models/__init__.py
    - tests/__init__.py
    - tests/test_import.py
  modified:
    - .gitignore

key-decisions:
  - "Used Python 3.13 in .python-version (not 3.11) because 3.13.7 is installed locally; satisfies requires-python>=3.11"
  - "Restricted pre-commit mypy hook to src/ files only (files: ^src/) so isolated hook env does not fail on tests/ imports"
  - "Added ignore_missing_imports=true to tests.* mypy override for local mypy runs"
  - "Added tests/test_import.py smoke test so pytest --collect-only exits 0 (not exit code 5 with zero tests)"

patterns-established:
  - "Pattern: All tool config (ruff, mypy, pytest) in pyproject.toml [tool.X] sections — no separate config files"
  - "Pattern: pre-commit mypy hook scoped to src/ only; local mypy checks all"
  - "Pattern: uv.lock committed to git for exact reproducibility"

requirements-completed: [PARSE-04]

# Metrics
duration: 6min
completed: 2026-03-01
---

# Phase 01 Plan 01: Project Scaffold Summary

**uv src-layout project with pyproject.toml, ruff/mypy/pytest config, pre-commit hooks, and editable package install — scaffold that phases 2-9 extend without modification**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-01T14:26:36Z
- **Completed:** 2026-03-01T14:32:53Z
- **Tasks:** 1
- **Files modified:** 11

## Accomplishments
- Complete src-layout project scaffold: pyproject.toml, uv.lock, .pre-commit-config.yaml, .python-version, README.md
- `uv sync --all-groups` installs 24 packages (lxml, networkx, ruff, mypy, pytest, pre-commit) in one command from clean state
- `alteryx_diff` package importable via editable install; `uv run pytest` and `uv run mypy src/` both exit 0
- Pre-commit hooks installed and passing (ruff-check, ruff-format, mypy on src/, trailing-whitespace, end-of-file-fixer, check-yaml, check-toml, check-merge-conflict, debug-statements)
- `src/alteryx_diff/models/__init__.py` empty placeholder ready for Plan 02 to populate with six dataclasses

## Task Commits

Each task was committed atomically:

1. **Task 1: Initialize uv project scaffold** - `e9f8db9` (feat)
2. **Task 1 (deviation): Add smoke test + fix mypy pre-commit** - `2cfaacb` (test)

**Plan metadata:** _(final docs commit — see below)_

## Files Created/Modified
- `pyproject.toml` - Project metadata, requires-python>=3.11, uv_build backend, ruff/mypy/pytest config, dev dependency group
- `.pre-commit-config.yaml` - ruff-check, ruff-format, mypy (src/ only), pre-commit-hooks (6 hooks)
- `.python-version` - Pins 3.13 (locally installed, satisfies >=3.11)
- `README.md` - Project overview, installation, usage, development commands
- `uv.lock` - Exact pinned versions for all 24 packages (committed for reproducibility)
- `src/alteryx_diff/__init__.py` - `__version__ = "0.1.0"`
- `src/alteryx_diff/py.typed` - PEP 561 marker (empty file)
- `src/alteryx_diff/models/__init__.py` - Empty placeholder (Plan 02 populates)
- `tests/__init__.py` - Empty package marker
- `tests/test_import.py` - Import smoke test ensuring pytest exits 0
- `.gitignore` - Added .venv/, __pycache__/, .mypy_cache/, .ruff_cache/, .pytest_cache/, dist/, *.egg-info/

## Decisions Made
- Used Python 3.13 in `.python-version` instead of 3.11: 3.13.7 is installed locally and satisfies `requires-python = ">=3.11"`; avoids downloading 3.11 via uv managed python
- Restricted pre-commit mirrors-mypy hook to `files: ^src/` pattern: the hook runs in an isolated venv without the project package installed, so checking `tests/` files that import `alteryx_diff` would always fail with `import-not-found`; local `uv run mypy src/` checks full src/ cleanly
- Added `ignore_missing_imports = true` to `tests.*` mypy override: belt-and-suspenders for local mypy runs that check both src/ and tests/
- Added `tests/test_import.py` minimal smoke test: `pytest --collect-only` exits code 5 (not 0) with zero tests found; the plan requires exit 0

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added smoke test to satisfy pytest exit 0 requirement**
- **Found during:** Task 1 verification
- **Issue:** `pytest --collect-only` exits code 5 (no tests found) with an empty `tests/` dir; plan done criteria requires exit 0
- **Fix:** Added `tests/test_import.py` with `test_package_importable` that imports `alteryx_diff` and asserts `__version__ == "0.1.0"`
- **Files modified:** `tests/test_import.py`
- **Verification:** `uv run pytest --collect-only -q` exits 0, `uv run pytest -q` shows 1 passed
- **Committed in:** `2cfaacb`

**2. [Rule 1 - Bug] Fixed mypy pre-commit hook failing on tests/ imports**
- **Found during:** First commit attempt after adding smoke test
- **Issue:** mirrors-mypy hook runs in isolated venv; cannot find `alteryx_diff` package; `import-not-found` error on `tests/test_import.py`
- **Fix:** Added `files: ^src/` to pre-commit mypy hook; added `ignore_missing_imports = true` to `tests.*` mypy override in pyproject.toml
- **Files modified:** `.pre-commit-config.yaml`, `pyproject.toml`
- **Verification:** Pre-commit mypy hook skipped on test files (no files to check); `uv run mypy src/` still passes; commit succeeds
- **Committed in:** `2cfaacb`

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** Both fixes required for correctness — exit 0 requirement and usable pre-commit hooks. No scope creep.

## Issues Encountered
- `uv` binary not in standard `$PATH`; found at `/Users/laxmikantmukkawar/.cache/uv/archive-v0/bkiNW9PCUPjqEK-u4PtHi/uv-0.8.12.data/scripts/uv` — used absolute path throughout execution
- Pre-existing `venv/` directory from earlier project init; uv created `.venv/` instead; `.gitignore` updated to exclude both

## User Setup Required
None - no external service configuration required. Run `uv sync --all-groups` from project root to reproduce.

## Next Phase Readiness
- Scaffold complete; `uv sync`, `pytest`, and `pre-commit` all work from clean checkout
- `src/alteryx_diff/models/__init__.py` is empty placeholder ready for Plan 02 to populate with six frozen dataclasses (WorkflowDoc, AlteryxNode, AlteryxConnection, DiffResult, NodeDiff, EdgeDiff) and three NewTypes (ToolID, ConfigHash, AnchorName)
- No blockers for Plan 02

---
*Phase: 01-scaffold-and-data-models*
*Completed: 2026-03-01*
