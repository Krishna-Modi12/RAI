# Judge-facing demo

## Purpose

This demo makes the system’s central claim visible: a deviation should be explained
before it is called an equipment fault.

## Preparation

```powershell
.venv\Scripts\python.exe scripts\generate_data.py
.venv\Scripts\python.exe scripts\train.py
```

## Recommended five-minute flow

### 00:00 — Explain the question

RAI is not looking for the largest raw sensor value. It is asking whether an asset is
abnormal for its operating conditions and whether acting now is economically justified.

### 00:30 — Equipment case

```powershell
.venv\Scripts\python.exe scripts\demo.py --scenario gearbox_bearing_wear
```

Point out the expected-vs-actual residuals, persistence, peer result, environmental
verdict, similar cases, economics, and the final `AgentVerdict`.

### 02:00 — Environmental case

```powershell
.venv\Scripts\python.exe scripts\demo.py --scenario cloud_transient
.venv\Scripts\python.exe scripts\demo.py --scenario curtailment_window
```

The important observation is that a weather or curtailment explanation is not promoted
to an equipment conclusion.

### 03:00 — Sensor case

```powershell
.venv\Scripts\python.exe scripts\demo.py --scenario anemometer_drift
.venv\Scripts\python.exe scripts\demo.py --scenario sensor_freeze
```

The system should identify the measurement problem or escalate instead of recommending
drivetrain work.

### 04:00 — Solar recovery case

```powershell
.venv\Scripts\python.exe scripts\demo.py --scenario soiling_accumulation
.venv\Scripts\python.exe scripts\demo.py --scenario string_outage
```

Contrast recoverable soiling with an equipment-side DC string event. Both are represented
by structured evidence, not a free-form chat claim.

## What is and is not shown

The command-line demo exercises the implemented simulator, stores, models, economics,
memory, and deterministic agent fallback. It does not claim a finished browser dashboard:
the Next.js app is still a scaffold and the FastAPI endpoint layer is still being wired to
the frozen contract.

