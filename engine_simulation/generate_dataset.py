"""
generate_dataset.py

Batch dataset generator for the digital-twin engine health monitoring project.
Produces a varied, reproducible set of simulated missions for downstream
anomaly-detection and RUL model training.

Usage:
    python engine_simulation/generate_dataset.py

Outputs:
    engine_simulation/data/dataset/mission_000.csv  ..  mission_179.csv
    engine_simulation/data/dataset/manifest.csv
"""

import csv
import os
import random
import sys

# Ensure project root is importable regardless of working directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_simulation.engine_simulator import (
    FAULT_FUNCTIONS,
    RPM_MAX_CONTINUOUS,
    simulate_mission,
    simulate_mission_variable_profile,
    save_records,
)

# ── Configuration ────────────────────────────────────────────────────

SEED = 42
N_MISSIONS = 180
HEALTHY_FRACTION = 0.30

# Per-fault ramp ranges (min_s, max_s).
# Fast-manifesting faults get shorter ramps; thermal faults are slower.
RAMP_RANGES = {
    "oil_pressure_fault":            (200, 500),
    "misfire_fault":                 (60,  200),
    "combustion_instability_fault":  (200, 500),
    "overheating_fault":             (400, 900),
    "alternator_fault":              (60,  200),
    "sensor_drift_fault":            (200, 600),
}

# Flight-profile randomisation bounds.
RPM_RANGE = (4300, RPM_MAX_CONTINUOUS)   # normal operating band from the manual
ALT_RANGE = (500, 5000)                  # metres; covers low-altitude + high-altitude ops
DURATION_RANGE = (1200, 2400)            # seconds (20 – 40 min missions)
FAULT_START_RANGE = (300, 1200)          # seconds into the mission

# Rapid-throttle-transition parameters.
RAPID_THROTTLE_PROBABILITY = 0.20        # ~20% of all missions
N_TRANSITIONS_RANGE = (2, 4)             # number of mid-cruise RPM changes
TRANSITION_RPM_DELTA = (300, 800)        # magnitude of each RPM step-change
TRANSITION_HOLD_RANGE = (60, 180)        # seconds at each new RPM setpoint
TRANSITION_RAMP_S = 10                   # seconds to linearly ramp between RPM setpoints

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data", "dataset")

# ── Helpers ──────────────────────────────────────────────────────────


def _random_rpm_schedule(cruise_rpm, cruise_start_s, cruise_end_s):
    """Build a random schedule of mid-cruise RPM step-changes."""
    n_transitions = random.randint(*N_TRANSITIONS_RANGE)
    schedule = []
    t = cruise_start_s + random.uniform(30, 120)  # first transition after settling
    for _ in range(n_transitions):
        if t + TRANSITION_RAMP_S + 30 > cruise_end_s:
            break  # not enough cruise time left
        delta = random.randint(*TRANSITION_RPM_DELTA) * random.choice([-1, 1])
        target = max(RPM_RANGE[0], min(RPM_RANGE[1], cruise_rpm + delta))
        schedule.append((t, target, TRANSITION_RAMP_S))
        hold = random.randint(*TRANSITION_HOLD_RANGE)
        t += TRANSITION_RAMP_S + hold
    return schedule


def _generate_one_mission(mission_id, fault_type, rng):
    """Generate a single mission dict and its records."""
    cruise_rpm = rng.randint(*RPM_RANGE)
    altitude_m = rng.randint(ALT_RANGE[0] // 100, ALT_RANGE[1] // 100) * 100  # 100 m steps
    duration_s = rng.randint(*DURATION_RANGE)
    has_rapid = rng.random() < RAPID_THROTTLE_PROBABILITY

    fault_start_s = None
    fault_ramp_s = None
    if fault_type:
        ramp_lo, ramp_hi = RAMP_RANGES[fault_type]
        fault_start_s = rng.randint(*FAULT_START_RANGE)
        # Ensure fault starts before the descent phase
        fault_start_s = min(fault_start_s, duration_s - 240)
        fault_ramp_s = rng.randint(ramp_lo, ramp_hi)

    # Choose simulation function based on whether rapid-throttle is needed.
    if has_rapid:
        climb_s = 120
        descent_s = 120
        cruise_start = climb_s
        cruise_end = duration_s - descent_s
        rpm_schedule = _random_rpm_schedule(cruise_rpm, cruise_start, cruise_end)
        # Only count as rapid throttle if we actually got transitions
        has_rapid = len(rpm_schedule) >= 2
        records = simulate_mission_variable_profile(
            duration_s=duration_s,
            cruise_rpm=cruise_rpm,
            altitude_m=float(altitude_m),
            rpm_schedule=rpm_schedule if has_rapid else None,
            fault_type=fault_type,
            fault_start_s=fault_start_s,
            fault_ramp_s=fault_ramp_s,
        )
    else:
        records = simulate_mission(
            duration_s=duration_s,
            cruise_rpm=cruise_rpm,
            altitude_m=float(altitude_m),
            fault_type=fault_type,
            fault_start_s=fault_start_s,
            fault_ramp_s=fault_ramp_s,
        )

    meta = {
        "mission_id": mission_id,
        "fault_type": fault_type or "none",
        "fault_start_s": fault_start_s if fault_type else "",
        "fault_ramp_s": fault_ramp_s if fault_type else "",
        "cruise_rpm": cruise_rpm,
        "altitude_m": altitude_m,
        "duration_s": duration_s,
        "has_rapid_throttle_transition": has_rapid,
    }
    return records, meta


# ── Main ─────────────────────────────────────────────────────────────


def generate_dataset(n_missions=N_MISSIONS, seed=SEED):
    random.seed(seed)
    rng = random  # use the module-level RNG (seeded above)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Distribute missions ──
    n_healthy = int(n_missions * HEALTHY_FRACTION)
    fault_types = sorted(FAULT_FUNCTIONS.keys())
    n_faulted = n_missions - n_healthy
    per_fault = n_faulted // len(fault_types)
    remainder = n_faulted - per_fault * len(fault_types)

    mission_plan = []
    # Healthy missions
    for _ in range(n_healthy):
        mission_plan.append(None)
    # Faulted missions, distributed evenly with remainder spread across first types
    for i, ft in enumerate(fault_types):
        count = per_fault + (1 if i < remainder else 0)
        for _ in range(count):
            mission_plan.append(ft)

    rng.shuffle(mission_plan)  # interleave healthy and faulted

    # ── Generate ──
    manifest_rows = []
    for idx, fault_type in enumerate(mission_plan):
        mission_id = f"mission_{idx:03d}"
        records, meta = _generate_one_mission(mission_id, fault_type, rng)

        csv_path = os.path.join(OUTPUT_DIR, f"{mission_id}.csv")
        save_records(records, csv_path)
        manifest_rows.append(meta)

        if (idx + 1) % 20 == 0 or idx == len(mission_plan) - 1:
            print(f"  Generated {idx + 1}/{len(mission_plan)} missions...")

    # ── Write manifest ──
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.csv")
    fieldnames = [
        "mission_id", "fault_type", "fault_start_s", "fault_ramp_s",
        "cruise_rpm", "altitude_m", "duration_s", "has_rapid_throttle_transition",
    ]
    with open(manifest_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in manifest_rows:
            writer.writerow(row)

    # ── Summary ──
    from collections import Counter
    fault_counts = Counter(r["fault_type"] for r in manifest_rows)
    altitudes = [r["altitude_m"] for r in manifest_rows]
    durations = [r["duration_s"] for r in manifest_rows]
    rapid_count = sum(1 for r in manifest_rows if r["has_rapid_throttle_transition"])

    print("\n" + "=" * 60)
    print("DATASET GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Total missions:    {len(manifest_rows)}")
    print(f"  Output directory:  {OUTPUT_DIR}")
    print(f"  Manifest:          {manifest_path}")
    print()
    print("  Missions per fault type:")
    for ft in sorted(fault_counts):
        print(f"    {ft:40s} {fault_counts[ft]:>4d}")
    print()
    print(f"  Altitude range:    {min(altitudes)} – {max(altitudes)} m")
    print(f"  Duration range:    {min(durations)} – {max(durations)} s")
    print(f"  Rapid-throttle:    {rapid_count} missions ({100*rapid_count/len(manifest_rows):.1f}%)")
    print("=" * 60)


if __name__ == "__main__":
    generate_dataset()
