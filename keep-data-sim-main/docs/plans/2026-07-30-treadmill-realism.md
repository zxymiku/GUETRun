# Treadmill Metric Realism Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate smoothly varying treadmill speed, heart rate, cadence, and derived step length that match the temporal distribution of the supplied Garmin activity while preserving requested summary targets.

**Architecture:** Add treadmill-specific correlated metric generators driven by the existing random seed. Keep the base pace strategy timeline, perturb and normalize speed to exact integrated distance, generate heart-rate warm-up/drift and correlated cadence, then derive step length in the FIT exporter.

**Tech Stack:** Python 3.10+, NumPy, Garmin FIT Python SDK, unittest/pytest

---

### Task 1: Statistical regression tests

**Files:**
- Create: `tests/test_treadmill_realism.py`

**Steps:**

1. Generate a deterministic 10 km treadmill activity at 5:54/km, HR 152, cadence 172.
2. Assert exact distance and 3540-second duration.
3. Assert nonzero but bounded speed variation and high lag-one correlation.
4. Assert heart-rate warm-up/drift, exact target mean after rounding, and bounded per-second changes.
5. Assert cadence target, standard deviation, lag-one correlation, and bounded per-second changes.
6. Export/decode FIT and assert step-length distribution, no GPS, treadmill subtype, CRC, and summary targets.
7. Run `python -m pytest tests/test_treadmill_realism.py -q` and confirm failure against the constant/white-noise model.

### Task 2: Correlated treadmill metric generators

**Files:**
- Create: `keep_data_sim/metrics/treadmill.py`

**Steps:**

1. Implement a normalized AR(1) helper using the provided NumPy generator.
2. Implement speed perturbation with high temporal correlation and exact trapezoidal-distance normalization.
3. Implement heart-rate warm-up, cardiac drift, correlated sensor variation, clipping, and target-mean centering.
4. Implement cadence as target plus speed coupling and correlated low-amplitude variation.
5. Unit-test deterministic output and statistical bounds.

### Task 3: Simulation integration

**Files:**
- Modify: `keep_data_sim/core/treadmill.py`
- Modify: `keep_data_sim/export/fit_exporter.py`

**Steps:**

1. Preserve the existing base pace timeline.
2. Replace constant speed records with the normalized realistic speed curve.
3. Recompute cumulative distance using trapezoidal integration and pin the final sample to the target distance.
4. Use treadmill-specific heart-rate and cadence curves.
5. Round rather than truncate average heart rate in FIT summaries.
6. Run treadmill and exporter regression tests.

### Task 4: End-to-end artifact and comparison

**Files:**
- Create (ignored artifact): `generated/Run_10K_Treadmill_Realistic_Pace_554_HR152_Cadence172_Garmin.fit`

**Steps:**

1. Run the complete test suite.
2. Generate the requested activity with a fixed seed.
3. Decode with CRC checking and calculate mean, standard deviation, quantiles, adjacent-change percentiles, and lag-one correlation for all four metrics.
4. Verify 10000 m, 3540 s, HR 152, cadence 172, treadmill subtype, and zero GPS/altitude fields.
5. Run `git diff --check` and report the artifact path.
