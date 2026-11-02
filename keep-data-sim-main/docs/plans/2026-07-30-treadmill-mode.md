# Treadmill FIT Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate Garmin-compatible treadmill running FIT activities without GPS coordinates or synthetic routes.

**Architecture:** Add a treadmill flag to configuration and CLI. Route treadmill simulations through a dedicated one-second time/distance generator, then make the FIT exporter mark all summaries as treadmill and omit position and altitude fields.

**Tech Stack:** Python 3.10+, NumPy, Garmin FIT Python SDK, unittest/pytest

---

### Task 1: Treadmill behavior tests

**Files:**
- Create: `tests/test_treadmill_mode.py`

**Steps:**

1. Add tests for CLI `--treadmill`, FIT-only default output, invalid cycling mode, and invalid explicit GPX output.
2. Add a simulator test that asserts 1000 m at 6:00/km produces 360 seconds with one record per second and never calls the route generator.
3. Add an exporter test that decodes with CRC checking and asserts treadmill sub-sport, zero position/altitude fields, running cadence, and step length.
4. Run `python -m pytest tests/test_treadmill_mode.py -q` and confirm the new tests fail before implementation.

### Task 2: Configuration and CLI

**Files:**
- Modify: `keep_data_sim/config/schema.py`
- Modify: `keep_data_sim/cli.py`
- Modify: `keep_data_sim/utils/validation.py`

**Steps:**

1. Add `treadmill: bool = False` to `SimConfig`.
2. Add `--treadmill` to the Basic CLI group.
3. Make `--format` default conditional: normal mode gets GPX and FIT; treadmill mode gets FIT only.
4. Reject treadmill cycling and treadmill configurations containing non-FIT formats.
5. Run the CLI and validation tests.

### Task 3: One-second treadmill simulation

**Files:**
- Modify: `keep_data_sim/core/simulator.py`
- Test: `tests/test_treadmill_mode.py`

**Steps:**

1. Branch `simulate()` to a dedicated `_simulate_treadmill()` method.
2. Advance distance with the selected pace strategy at one-second intervals and use a fractional final interval when needed.
3. Generate heart rate and cadence from the resulting speed/timestamp arrays.
4. Use a flat elevation and placeholder internal coordinate while preserving exact target distance.
5. Include `mode: treadmill` in the summary and run the simulator tests.

### Task 4: Garmin treadmill FIT export

**Files:**
- Modify: `keep_data_sim/export/fit_exporter.py`
- Test: `tests/test_treadmill_mode.py`

**Steps:**

1. Write sub-sport treadmill to Sport, Lap, and Session messages.
2. Omit position latitude, position longitude, and altitude from treadmill Record messages.
3. Retain distance, speed, heart rate, half-cadence plus fractional cadence, total strides, and step length.
4. Decode with CRC checking and assert all field-level expectations.

### Task 5: Documentation and end-to-end artifact

**Files:**
- Modify: `README.md`
- Create (ignored artifact): `generated/Run_10K_Treadmill_Pace_600_HR153_Garmin.fit`

**Steps:**

1. Document `--treadmill`, FIT-only behavior, and a 10 km command example.
2. Run the complete test suite with `python -m pytest -q`.
3. Generate 10 km at 6:00/km, average HR 153, cadence 170 spm, and no warm-up slowdown.
4. Decode the output with CRC checking and verify 10000 m, 3600 s, HR 153, treadmill sub-sport, zero GPS fields, and plausible cadence/step length.
5. Run `git diff --check` and inspect final status.
