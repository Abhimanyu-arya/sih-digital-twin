"""
signed_error_analysis.py

1. Computes mean signed error (pred - true) and % under- vs over-prediction per fault type.
2. Inspects post-failure behavior (t after true RUL reaches 0) to detect RUL rebound bumps.
"""

import os
import sys
import numpy as np
import pandas as pd
import torch
from collections import defaultdict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai_layer.rul_estimation.train_rul_model import RULConvNet, WINDOW_SIZE, SEED, DATASET_DIR
from ai_layer.rul_estimation.evaluate_rul_model import get_test_missions

MODEL_PATH = os.path.join(os.path.dirname(__file__), "../ai_layer/rul_estimation/rul_model.pt")

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=False)
    features = checkpoint['features']
    scaler_mean = checkpoint['scaler_mean']
    scaler_scale = checkpoint['scaler_scale']
    
    model = RULConvNet(in_channels=len(features)).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    test_ids, fault_types = get_test_missions()
    first_det_df = pd.read_csv(os.path.join(DATASET_DIR, "first_detections.csv"))
    det_map = dict(zip(first_det_df["mission_id"], first_det_df["t_first_detected"]))
    labels_df = pd.read_csv(os.path.join(DATASET_DIR, "rul_labels.csv"))
    
    fault_signed_errors = defaultdict(list)
    fault_under_counts = defaultdict(int)
    fault_over_counts = defaultdict(int)
    fault_exact_counts = defaultdict(int)
    fault_total_counts = defaultdict(int)
    
    post_failure_bump_missions = set()
    max_bump_magnitude = 0.0
    
    for mid in test_ids:
        ft = fault_types[mid]
        if mid not in det_map or pd.isnull(det_map[mid]):
            continue
            
        t_det = det_map[mid]
        raw_df = pd.read_csv(os.path.join(DATASET_DIR, f"{mid}.csv"))
        res_df = pd.read_csv(os.path.join(DATASET_DIR, f"residuals_{mid.replace('mission_', '')}.csv"))
        lbl_df = labels_df[labels_df["mission_id"] == mid]
        
        merged = pd.merge(raw_df, res_df, on="timestamp")
        merged = pd.merge(merged, lbl_df, on="timestamp")
        merged["time_since_detection"] = merged["timestamp"] - t_det
        merged = merged[merged["timestamp"] >= t_det].reset_index(drop=True)
        
        if len(merged) < WINDOW_SIZE:
            continue
            
        x_raw = merged[features].values
        rul_true = merged["rul_seconds"].values
        timestamps = merged["timestamp"].values
        
        x_scaled = (x_raw - scaler_mean) / scaler_scale
        
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
            
        preds_real = np.expm1(preds_log)
        preds_real = np.maximum(0.0, preds_real)
        
        reached_zero_pred = False
        
        for i in range(len(preds_real)):
            p = preds_real[i]
            t = true_ruls[i]
            diff = p - t
            
            fault_signed_errors[ft].append(diff)
            fault_total_counts[ft] += 1
            
            if diff < -0.01:
                fault_under_counts[ft] += 1
            elif diff > 0.01:
                fault_over_counts[ft] += 1
            else:
                fault_exact_counts[ft] += 1
                
            # Post-failure check: when true RUL == 0
            if t == 0.0:
                if p <= 1.0:
                    reached_zero_pred = True
                elif reached_zero_pred and p > 1.0:
                    post_failure_bump_missions.add(mid)
                    if p > max_bump_magnitude:
                        max_bump_magnitude = p
                        
    print("\n" + "="*80)
    print("SIGNED ERROR ANALYSIS (PREDICTED - TRUE RUL)")
    print("Negative = Under-prediction (Conservative / Safe) | Positive = Over-prediction")
    print("="*80)
    print(f"{'Fault Type':<30} | {'Mean Signed Err':<16} | {'Under-predict %':<16} | {'Over-predict %':<16}")
    print("-" * 80)
    
    all_signed = []
    for ft in sorted(fault_signed_errors.keys()):
        errs = fault_signed_errors[ft]
        all_signed.extend(errs)
        mean_err = np.mean(errs)
        tot = fault_total_counts[ft]
        under_pct = (fault_under_counts[ft] / tot) * 100
        over_pct = (fault_over_counts[ft] / tot) * 100
        
        print(f"{ft:<30} | {mean_err:13.2f} s | {under_pct:14.1f}% | {over_pct:14.1f}%")
        
    print("-" * 80)
    all_under = sum(fault_under_counts.values())
    all_over = sum(fault_over_counts.values())
    all_tot = sum(fault_total_counts.values())
    print(f"{'OVERALL AVERAGE':<30} | {np.mean(all_signed):13.2f} s | {(all_under/all_tot)*100:14.1f}% | {(all_over/all_tot)*100:14.1f}%")
    print("="*80 + "\n")
    
    print("="*80)
    print("POST-FAILURE MONOTONICITY & BUMP CHECK")
    print("="*80)
    print(f"Missions exhibiting post-failure RUL rebound bumps: {len(post_failure_bump_missions)} / {len(test_ids)}")
    print(f"Max post-failure bump magnitude: {max_bump_magnitude:.2f} seconds")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
