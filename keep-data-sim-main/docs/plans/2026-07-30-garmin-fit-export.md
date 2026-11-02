# Garmin-Compatible FIT Export Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate FIT Activity files with Garmin-compatible timing, timezone, creator, cadence, stride, and step-length data.

**Architecture:** Extend `SimConfig` with an IANA timezone and expose it through the simulation CLI. Update `FitExporter` to emit creator device info, timer start/stop events, and an activity-local timestamp while retaining summary-last ordering. Convert running double-step cadence to FIT single-foot cycles, retain cycling rpm, integrate total cycles, and derive record/session step length.

**Tech Stack:** Python 3.10+, `garmin-fit-sdk`, `zoneinfo`, `pytest`/`unittest`

---

### Task 1: Garmin activity structure tests

**Files:**
- Create: `tests/test_fit_exporter.py`

**Steps:**

1. Encode a short activity with `FitExporter`.
2. Assert the test initially fails because creator info, events, or local timestamp are absent.
3. Verify the expected message order and required summary fields.

### Task 2: Timezone configuration

**Files:**
- Modify: `keep_data_sim/config/schema.py`
- Modify: `keep_data_sim/cli.py`
- Modify: `keep_data_sim/utils/validation.py`
- Modify: `tests/test_cli.py`

**Steps:**

1. Add `timezone_name` with default `Asia/Shanghai`.
2. Add simulation `--timezone` and pass it into `SimConfig`.
3. Reject invalid IANA timezone names.
4. Run CLI and validation tests.

### Task 3: FIT exporter compatibility

**Files:**
- Modify: `keep_data_sim/export/fit_exporter.py`
- Test: `tests/test_fit_exporter.py`

**Steps:**

1. Use the development manufacturer ID and product name.
2. Write creator Device Info and Timer Start before records.
3. Write Timer Stop after records.
4. Add `activity.local_timestamp` derived from the configured timezone.
5. Decode with CRC checking and assert all structural tests pass.
6. Assert running cadence, total strides, and step length use Garmin units.
7. Assert cycling cadence remains unchanged and has no running step-length field.

### Task 4: Documentation and end-to-end verification

**Files:**
- Modify: `README.md`

**Steps:**

1. Document simulation `--timezone` and Garmin-compatible FIT structure.
2. Run `pytest -q`.
3. Generate running and cycling FIT samples and decode both with CRC checking.
4. Run `git diff --check` and inspect the final diff.
