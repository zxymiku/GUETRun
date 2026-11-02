# FIT Date Shift Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Garmin-compatible command that changes an existing FIT activity to a specified local start time.

**Architecture:** Decode the complete FIT stream with Garmin FIT SDK listeners, calculate one UTC offset from the canonical activity start, recursively shift decoded datetime values, and re-encode messages in original order with developer field definitions. Verify the generated file by decoding it again with CRC checking enabled.

**Tech Stack:** Python 3.10+, `garmin-fit-sdk`, `zoneinfo`, `argparse`, `pytest`/`unittest`

---

### Task 1: FIT shifting core

**Files:**
- Create: `keep_data_sim/fit_shift.py`
- Create: `tests/test_fit_shift.py`

**Steps:**

1. Write tests that create a minimal activity FIT file, shift it to a Beijing start time, and assert the new UTC start, unchanged duration and unchanged track metrics.
2. Run `pytest tests/test_fit_shift.py -v` and verify it fails because the module does not exist.
3. Implement ordered decoding, canonical start detection, recursive datetime shifting, developer field preservation, safe output handling, and CRC verification.
4. Run `pytest tests/test_fit_shift.py -v` and verify all core tests pass.

### Task 2: CLI subcommand

**Files:**
- Modify: `keep_data_sim/cli.py`
- Modify: `tests/test_cli.py`

**Steps:**

1. Add failing tests for `shift-fit`, required arguments, default timezone/output behavior, and command dispatch.
2. Refactor the parser to use `simulate` compatibility plus a `shift-fit` subcommand without breaking existing top-level simulation arguments.
3. Connect `shift-fit` to the core function and print the resulting output path and old/new UTC start times.
4. Run `pytest tests/test_cli.py tests/test_fit_shift.py -v`.

### Task 3: Documentation and verification

**Files:**
- Modify: `README.md`

**Steps:**

1. Document the new command, Beijing-time default, non-overwrite behavior, and Garmin CRC revalidation.
2. Run `pytest -v`.
3. Run a manual CLI round trip against a generated FIT fixture and decode the result with CRC checking enabled.
4. Inspect `git diff --check` and `git status --short`.
