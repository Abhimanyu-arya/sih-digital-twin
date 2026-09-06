"""
compute_first_detections.py

Iterates over all faulted missions in the dataset, runs the residual anomaly detector timestamp-by-timestamp,
and records t_first_detected (the timestamp of the FIRST magnitude or trend anomaly trigger).
Computes and reports min/max/mean detection delay relative to true fault_start_s.
Outputs findings to engine_simulation/data/dataset/first_detections.csv.
"""

import os
import sys
import pandas as pd
import numpy as np
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from ai_layer.anomaly_detection.residual_detector import process_timestamp

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../engine_simulation/data/dataset"))

def main():
    summary_df = pd.read_csv(os.path.join(DATASET_DIR, "rul_summary.csv"))
    manifest_df = pd.read_csv(os.path.join(DATASET_DIR, "manifest.csv"))
    
    summary_df = pd.merge(summary_df, manifest_df[["mission_id", "fault_start_s"]], on="mission_id")
    
    # Exclude healthy and sensor_drift_fault (where excluded_reason is populated)
    valid_missions = summary_df[summary_df["excluded_reason"].isnull() | (summary_df["excluded_reason"] == "")].copy()
    
    records = []
    
    print(f"Processing {len(valid_missions)} faulted missions for anomaly detection...")
    
    for idx, row in valid_missions.iterrows():
        mid = row["mission_id"]
        fault_type = row["fault_type"]
        fault_start_s = row["fault_start_s"]
        
        mission_path = os.path.join(DATASET_DIR, f"{mid}.csv")
        df = pd.read_csv(mission_path)
        
        history = {}
        t_first_detected = None
        first_trigger_channel = None
        first_trigger_type = None
        
        anom_streak = 0
        for _, timestamp_row in df.iterrows():
            row_dict = timestamp_row.to_dict()
            res = process_timestamp(row_dict, history)
            
            # Check if any channel triggered an anomaly
            any_anom = any(ch_res['is_anomaly'] for ch_res in res['channels'].values())
            if any_anom:
                anom_streak += 1
            else:
                anom_streak = 0
                
            # Require 3 consecutive anomalous timestamps to filter single 1-second noise spikes
            if anom_streak >= 3:
                t_first_detected = res['timestamp'] - 2.0
                # Find channel that triggered
                for ch, ch_res in res['channels'].items():
                    if ch_res['is_anomaly']:
                        first_trigger_channel = ch
                        first_trigger_type = ch_res['trigger']
                        break
                break
                
        if t_first_detected is not None:
            delay = t_first_detected - fault_start_s
        else:
            # If never detected before mission end
            delay = np.nan
            t_first_detected = np.nan
            
        records.append({
            "mission_id": mid,
            "fault_type": fault_type,
            "fault_start_s": fault_start_s,
            "t_first_detected": t_first_detected,
            "detection_delay_s": delay,
            "first_trigger_channel": first_trigger_channel,
            "first_trigger_type": first_trigger_type
        })
        
    res_df = pd.DataFrame(records)
    out_csv = os.path.join(DATASET_DIR, "first_detections.csv")
    res_df.to_csv(out_csv, index=False)
    print(f"Saved first detection results to {out_csv}")
    
    print("\n" + "="*70)
    print("ANOMALY DETECTION TIMING DISTRIBUTION (t_first_detected - fault_start_s)")
    print("="*70)
    
    grouped = res_df.groupby("fault_type")["detection_delay_s"]
    for ft, group in grouped:
        print(f"\nFault Type: {ft} (N={len(group)})")
        print(f"  Min delay  : {group.min():.2f} s")
        print(f"  Max delay  : {group.max():.2f} s")
        print(f"  Mean delay : {group.mean():.2f} s")
        print(f"  Median     : {group.median():.2f} s")
        
    overall = res_df["detection_delay_s"]
    print("\n" + "-"*70)
    print(f"OVERALL Across All {len(res_df)} Faulted Missions:")
    print(f"  Min delay  : {overall.min():.2f} s")
    print(f"  Max delay  : {overall.max():.2f} s")
    print(f"  Mean delay : {overall.mean():.2f} s")
    print(f"  Median     : {overall.median():.2f} s")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
