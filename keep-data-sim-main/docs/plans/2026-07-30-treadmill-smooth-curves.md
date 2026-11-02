# Treadmill Smooth Curves Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove visible one-second sawtooth changes from treadmill metrics while preserving the Garmin-calibrated distributions and requested summary values.

**Architecture:** Replace point-by-point AR innovations with correlated control points spaced 20–30 seconds apart. Interpolate between anchors, soften corners with a short centered window, standardize the result, and retain exact distance normalization plus physically derived step length.

**Tech Stack:** Python 3.10+, NumPy, Garmin FIT Python SDK, unittest/pytest

---

### Task 1: Smoothness regression

**Files:**
- Modify: `tests/test_treadmill_realism.py`

**Steps:**

1. Add a direction-reversal metric for adjacent first differences.
2. Assert speed reversal ratio below 12%, cadence below 10%, and FIT step length below 20%.
3. Run the targeted tests and verify they fail against the pointwise AR model.

### Task 2: Control-point curve generator

**Files:**
- Modify: `keep_data_sim/metrics/treadmill.py`

**Steps:**

1. Generate correlated anchor values at a configurable interval.
2. Linearly interpolate anchors to one-second samples.
3. Apply a centered Hann window with edge padding to soften anchor corners.
4. Normalize the curve to zero mean and unit variance.
5. Use 30-second controls for speed, 20-second controls for cadence, and 20-second controls for HR sensor variation.
6. Remove isolated per-sample target-mean corrections that can create one-point spikes.

### Task 3: Statistical and FIT verification

**Files:**
- Test: `tests/test_treadmill_realism.py`

**Steps:**

1. Verify speed/cadence/step-length standard deviations remain within Garmin-derived bounds.
2. Verify lag-one correlations remain high and direction reversals drop sharply.
3. Verify 10 km/59:00, HR 152, cadence 172, treadmill subtype, CRC, and zero GPS.
4. Run the complete test suite and `git diff --check`.

### Task 4: Generate 10.3 km artifact

**Files:**
- Create (ignored artifact): `generated/Run_10_3K_Treadmill_Smooth_Pace_554_HR152_Cadence172_Garmin.fit`

**Steps:**

1. Generate 10.3 km at 5:54/km, HR 152, cadence 172 with the fixed seed.
2. Decode and verify 10300 m, 3646.2 seconds, smoothness metrics, summary targets, CRC, treadmill subtype, and zero GPS.
