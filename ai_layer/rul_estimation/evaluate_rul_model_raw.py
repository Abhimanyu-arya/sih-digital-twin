"""
evaluate_rul_model.py

Evaluates the trained 1D CNN RUL model:
1. Generates Predicted vs True RUL plots for sample test missions (saved as PNG).
2. Computes MAE specifically for the near-failure region (<60s) vs early regions.
3. Checks for physically nonsensical increasing RUL predictions.
"""

import os
import sys
import random
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
from collections import defaultdict

# Import network architecture and constants
sys.path.insert(0, os.path.dirname(__file__))
from train_rul_model import RULConvNet, WINDOW_SIZE, SEED

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../engine_simulation/data/dataset"))
MODEL_PATH = os.path.join(os.path.dirname(__file__), "rul_model_raw.pt")
OUTPUT_DIR = os.path.dirname(__file__)


def get_test_missions():
    """Reproduce the random split from train_rul_model.py to get the test set mission IDs."""
    random.seed(SEED)
    
    summary_df = pd.read_csv(os.path.join(DATASET_DIR, "rul_summary.csv"))
    valid_missions = summary_df[summary_df["excluded_reason"].isnull() | (summary_df["excluded_reason"] == "")]
    mission_ids = valid_missions["mission_id"].tolist()
    
    random.shuffle(mission_ids)
    n = len(mission_ids)
    test_ids = mission_ids[int(n * 0.85):]
    
    fault_types = dict(zip(valid_missions["mission_id"], valid_missions["fault_type"]))
    return test_ids, fault_types


def extract_windows_for_mission(mid, fault_type):
    """Loads a single mission and prepares 60-step windows."""
    raw_df = pd.read_csv(os.path.join(DATASET_DIR, f"{mid}.csv"))
    res_df = pd.read_csv(os.path.join(DATASET_DIR, f"residuals_{mid.replace('mission_', '')}.csv"))
    lbl_df = pd.read_csv(os.path.join(DATASET_DIR, "rul_labels.csv"))
    lbl_df = lbl_df[lbl_df["mission_id"] == mid]
    
    merged = pd.merge(raw_df, res_df, on="timestamp")
    merged = pd.merge(merged, lbl_df, on="timestamp")
    
    if len(merged) < WINDOW_SIZE:
        return None, None, None
        
    return merged, fault_type


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}")
        return
        
    checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=False)
    features = checkpoint['features']
    scaler_mean = checkpoint['scaler_mean']
    scaler_scale = checkpoint['scaler_scale']
    
    model = RULConvNet(in_channels=len(features)).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    test_ids, fault_types = get_test_missions()
    print(f"Loaded {len(test_ids)} test missions.")
    
    # 1. Evaluate metrics
    near_failure_errors = defaultdict(list)
    far_failure_errors = defaultdict(list)
    
    missions_with_increase = 0
    
    # For plotting, pick one of each major fault type
    plotted_faults = set()
    target_plot_faults = {"oil_pressure_fault", "misfire_fault", "overheating_fault"}
    
    for mid in test_ids:
        ft = fault_types[mid]
        merged, _ = extract_windows_for_mission(mid, ft)
        if merged is None:
            continue
            
        x_raw = merged[features].values
        rul_true = merged["rul_seconds"].values
        timestamps = merged["timestamp"].values
        
        # Scale
        x_scaled = (x_raw - scaler_mean) / scaler_scale
        
        # Build windows
        windows = []
        true_ruls = []
        window_timestamps = []
        
        for i in range(len(x_scaled) - WINDOW_SIZE + 1):
            windows.append(x_scaled[i:i + WINDOW_SIZE, :])
            true_ruls.append(rul_true[i + WINDOW_SIZE - 1])
            window_timestamps.append(timestamps[i + WINDOW_SIZE - 1])
            
        windows_tensor = torch.tensor(np.array(windows), dtype=torch.float32).transpose(1, 2).to(device)
        
        with torch.no_grad():
            preds_log = model(windows_tensor).cpu().numpy()
            
        preds_real = preds_log
        
        # Metrics collection
        has_increase = False
        for i in range(len(preds_real)):
            err = abs(preds_real[i] - true_ruls[i])
            if true_ruls[i] < 60:
                near_failure_errors[ft].append(err)
            else:
                far_failure_errors[ft].append(err)
                
            # Check monotonically increasing (if prediction goes UP by more than 1 second to filter tiny noise)
            if i > 0 and (preds_real[i] - preds_real[i-1]) > 1.0:
                has_increase = True
                
        if has_increase:
            missions_with_increase += 1
            
        # Plotting
        if ft in target_plot_faults and ft not in plotted_faults:
            plt.figure(figsize=(10, 5))
            plt.plot(window_timestamps, true_ruls, label="True RUL", color="black", linestyle="--")
            plt.plot(window_timestamps, preds_real, label="Predicted RUL", color="red")
            plt.title(f"RUL Prediction over Time - {mid} ({ft})")
            plt.xlabel("Mission Time (s)")
            plt.ylabel("Remaining Useful Life (s)")
            plt.legend()
            plt.grid(True)
            plot_path = os.path.join(OUTPUT_DIR, f"rul_plot_{ft}_raw.png")
            plt.savefig(plot_path)
            plt.close()
            print(f"Saved plot: {plot_path}")
            plotted_faults.add(ft)
            
    print("\n--- MAE by Region and Fault Type ---")
    for ft in set(list(near_failure_errors.keys()) + list(far_failure_errors.keys())):
        near_errs = near_failure_errors.get(ft, [])
        far_errs = far_failure_errors.get(ft, [])
        
        near_mae = np.mean(near_errs) if near_errs else float('nan')
        far_mae = np.mean(far_errs) if far_errs else float('nan')
        
        print(f"{ft}:")
        print(f"  Near-failure (<60s) MAE : {near_mae:.2f} s (N={len(near_errs)})")
        print(f"  Early-region (>=60s) MAE: {far_mae:.2f} s (N={len(far_errs)})")
        
    print(f"\n--- Monotonicity Check ---")
    print(f"Missions showing increasing RUL predictions: {missions_with_increase} / {len(test_ids)} ({(missions_with_increase/len(test_ids))*100:.1f}%)")

if __name__ == "__main__":
    main()
