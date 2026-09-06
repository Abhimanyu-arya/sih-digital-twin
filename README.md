# AI-Enabled Real-Time Digital Twin for Aero Piston Engine Health Monitoring

**SIH Problem Statement:** SIH26054 — DRDO, Robotics and Drones, Software
**Team size:** 2

## What this is

A digital-twin system for health monitoring, fault prediction, and remaining
useful life (RUL) estimation of aero piston engines used in MALE UAVs.
The system mirrors a real engine's behaviour using a physics-informed
model, compares it against live/simulated sensor data (residual-based
anomaly detection), predicts remaining useful life, explains *why* an
anomaly was flagged, and presents all of this on an operator dashboard
with mission replay.

## The data-honesty statement (read this first)

No public dataset of real aero piston engine telemetry or run-to-failure
data exists. Rather than train and validate against our own synthetic
simulator alone (a circular setup), we grounded every part of this system
in real, publicly available sources:

- **Rotax 912 Series Operator's Manual** (official BRP-Rotax document) —
  used to calibrate normal operating limits, the RPM/power/fuel
  performance table, and 7 of our 8 fault signatures via its documented
  abnormal-operation and ignition-check procedures.
  See `docs/rotax_912_manual_notes.md`.
- **OpenEngineData.org** — real general-aviation piston engine flight
  logs (JPI engine monitor data), used to sanity-check sensor shape and
  noise characteristics against a real aircraft.
- **NASA C-MAPSS turbofan degradation dataset** — a different engine
  type, used only to validate that our RUL/anomaly-detection
  *methodology* works on real degradation data, not to represent piston
  engine behaviour.

See `docs/fault_grounding.md` for exactly which fault modes are
manual-grounded vs. purely synthetic. We say this openly in our pitch
rather than have a judge discover it.

## Repository structure

```
sih-digital-twin/
├── docs/                     Documentation & data-honesty artifacts
├── engine_simulation/        Physics-informed engine model + fault injection (Person A)
├── ai_layer/                 Anomaly detection, RUL estimation, explainability (Person B)
│   ├── anomaly_detection/
│   ├── rul_estimation/
│   └── explainability/
├── dashboard/                React operator dashboard + mission replay
└── requirements.txt
```

## Team split

- **Person A — Engine & Data:** `engine_simulation/`, fault definitions,
  RUL end-of-life threshold definition, data-honesty documentation.
- **Person B — AI & Product:** `ai_layer/`, `dashboard/`.

Both own the pitch narrative and demo script jointly.

## Getting started

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python engine_simulation/engine_simulator.py
```

This generates two demo missions in `engine_simulation/data/`: one with
a developing oil-pressure/lubrication fault, one with a developing
misfire fault — the inputs the AI layer and dashboard consume.
