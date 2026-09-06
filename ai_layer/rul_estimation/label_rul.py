"""
label_rul.py

Computes ground-truth RUL (Remaining Useful Life) labels for the generated
dataset missions, applying explicit human-defined end-of-life thresholds.

Outputs:
  - rul_labels.csv (per-timestamp RUL for each mission)
  - rul_summary.csv (mission-level summary)
"""

import csv
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from engine_simulation.engine_simulator import steady_state_engine

DATASET_DIR = os.path.join(os.path.dirname(__file__), "../../engine_simulation/data/dataset")
MANIFEST_PATH = os.path.join(DATASET_DIR, "manifest.csv")
OUT_LABELS_PATH = os.path.join(DATASET_DIR, "rul_labels.csv")
OUT_SUMMARY_PATH = os.path.join(DATASET_DIR, "rul_summary.csv")


def condition_breached(fault_type, row):
    """Evaluate whether the instantaneous sensor readings breach the threshold."""
    if fault_type == "oil_pressure_fault":
        return float(row["oil_pressure_bar"]) < 0.8
    elif fault_type == "overheating_fault":
        return float(row["cht_c"]) > 135.0 or float(row["oil_temp_c"]) > 130.0
    elif fault_type == "alternator_fault":
        return float(row["alternator_v"]) < 12.0
    elif fault_type in ("misfire_fault", "combustion_instability_fault"):
        baseline = steady_state_engine(float(row["commanded_rpm"]), float(row["altitude_m"]))
        if fault_type == "misfire_fault":
            drop = baseline["rpm"] - float(row["rpm"])
            return drop >= 300.0
        elif fault_type == "combustion_instability_fault":
            drop = baseline["egt_c"] - float(row["egt_c"])
            return drop >= 150.0
    return False


def get_sustained_window(fault_type):
    """Return the required sustained window (seconds) for a breach to count as failure."""
    return {
        "oil_pressure_fault": 10.0,
        "misfire_fault": 5.0,
        "combustion_instability_fault": 15.0,
        "alternator_fault": 30.0,
        "overheating_fault": 0.0,
    }.get(fault_type, 0.0)


def process_mission(mission_meta):
    mission_id = mission_meta["mission_id"]
    fault_type = mission_meta["fault_type"]
    fault_start_s = float(mission_meta["fault_start_s"]) if mission_meta["fault_start_s"] else None
    csv_path = os.path.join(DATASET_DIR, f"{mission_id}.csv")
    
    with open(csv_path, "r") as f:
        rows = list(csv.DictReader(f))
        
    excluded_reason = ""
    t_failure = None
    
    if fault_type == "none":
        excluded_reason = "healthy"
    elif fault_type == "sensor_drift_fault":
        excluded_reason = "sensor_drift (no physical EOL)"
    else:
        window_req = get_sustained_window(fault_type)
        breach_start = None
        
        for row in rows:
            t = float(row["timestamp"])
            if condition_breached(fault_type, row):
                if breach_start is None:
                    breach_start = t
                if t - breach_start >= window_req:
                    t_failure = t
                    break
            else:
                breach_start = None

        if t_failure is not None and fault_start_s is not None and t_failure < fault_start_s:
            print(f"  [WARNING] {mission_id}: Failure detected at {t_failure}s, BEFORE fault start at {fault_start_s}s. Noise artifact?")
            
    # Compute RUL for all rows
    labels = []
    for row in rows:
        t = float(row["timestamp"])
        if t_failure is not None:
            rul = max(0.0, t_failure - t)
        else:
            rul = float(rows[-1]["timestamp"]) - t  # Use remaining duration as ceiling if no failure
        labels.append({"mission_id": mission_id, "timestamp": row["timestamp"], "rul_seconds": round(rul, 2)})
        
    summary = {
        "mission_id": mission_id,
        "fault_type": fault_type,
        "t_failure": t_failure if t_failure is not None else "",
        "failure_reached": t_failure is not None,
        "excluded_reason": excluded_reason
    }
    
    return labels, summary


def main():
    if not os.path.exists(MANIFEST_PATH):
        print(f"Error: Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)
        
    with open(MANIFEST_PATH, "r") as f:
        manifest = list(csv.DictReader(f))
        
    all_labels = []
    all_summaries = []
    
    print(f"Processing {len(manifest)} missions...")
    
    for meta in manifest:
        labels, summary = process_mission(meta)
        all_labels.extend(labels)
        all_summaries.append(summary)
        
    # Write labels
    with open(OUT_LABELS_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["mission_id", "timestamp", "rul_seconds"])
        writer.writeheader()
        for lbl in all_labels:
            writer.writerow(lbl)
            
    # Write summary
    with open(OUT_SUMMARY_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["mission_id", "fault_type", "t_failure", "failure_reached", "excluded_reason"])
        writer.writeheader()
        for smry in all_summaries:
            writer.writerow(smry)
            
    # Print stats
    from collections import Counter
    print("\n--- RUL Labeling Summary ---")
    
    # Excluded missions
    excluded = [s for s in all_summaries if s["excluded_reason"]]
    print(f"Excluded missions: {len(excluded)} (Healthy or Sensor Drift)")
    
    # Evaluated missions
    evaluated = [s for s in all_summaries if not s["excluded_reason"]]
    reached = [s for s in evaluated if s["failure_reached"]]
    not_reached = [s for s in evaluated if not s["failure_reached"]]
    
    print(f"Faulted missions evaluated for RUL: {len(evaluated)}")
    print(f"  Reached EOL threshold: {len(reached)}")
    print(f"  Did NOT reach EOL: {len(not_reached)}")
    
    if len(not_reached) > 0:
        print("\nWARNING: Some missions did not reach EOL:")
        not_reached_counts = Counter(s["fault_type"] for s in not_reached)
        for ft, count in not_reached_counts.items():
            print(f"  {ft}: {count}")
    
    print(f"\nOutputs written to:\n  - {OUT_LABELS_PATH}\n  - {OUT_SUMMARY_PATH}")


if __name__ == "__main__":
    main()
