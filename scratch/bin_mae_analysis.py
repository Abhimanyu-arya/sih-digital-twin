"""
bin_mae_analysis.py

Bins post-detection windows into 3 equal time intervals (Bin 1: Early, Bin 2: Mid, Bin 3: Late)
from t_first_detected to t_failure for each test mission, and computes MAE per bin per fault type.
"""

import os
import sys
import numpy as np
import pandas as pd
import torch
from collections import defaultdict

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai_layer.rul_estimation.train_rul_model import RULConvNet, WINDOW_SIZE, SEED, DATASET_DIR, MODEL_PATH
from ai_layer.rul_estimation.evaluate_rul_model import get_test_missions

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
    
    bin_errors = {
        "Bin 1 (Early 33%)": defaultdict(list),
        "Bin 2 (Mid 33%)": defaultdict(list),
        "Bin 3 (Late 33%)": defaultdict(list)
    }
    
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
        
        # Post-detection only
        merged = merged[merged["timestamp"] >= t_det].reset_index(drop=True)
        if len(merged) < WINDOW_SIZE:
            continue
            
        t_start = merged["timestamp"].iloc[0]
        t_end = merged["timestamp"].iloc[-1]
        duration = t_end - t_start
        
        t_bin1_end = t_start + duration / 3.0
        t_bin2_end = t_start + 2.0 * duration / 3.0
        
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
        
        for i in range(len(preds_real)):
            err = abs(preds_real[i] - true_ruls[i])
            t = window_timestamps[i]
            
            if t <= t_bin1_end:
                bin_errors["Bin 1 (Early 33%)"][ft].append(err)
            elif t <= t_bin2_end:
                bin_errors["Bin 2 (Mid 33%)"][ft].append(err)
            else:
                bin_errors["Bin 3 (Late 33%)"][ft].append(err)
                
    print("\n" + "="*80)
    print("MAE BY POST-DETECTION ELAPSED TIME THIRD (PHM Uncertainty Narrowing Check)")
    print("="*80)
    
    all_faults = sorted(list(set(fault_types.values())))
    
    print(f"{'Fault Type':<30} | {'Bin 1 (Early)':<15} | {'Bin 2 (Mid)':<15} | {'Bin 3 (Late)':<15}")
    print("-" * 80)
    
    for ft in all_faults:
        b1_mae = np.mean(bin_errors["Bin 1 (Early 33%)"][ft]) if bin_errors["Bin 1 (Early 33%)"][ft] else float('nan')
        b2_mae = np.mean(bin_errors["Bin 2 (Mid 33%)"][ft]) if bin_errors["Bin 2 (Mid 33%)"][ft] else float('nan')
        b3_mae = np.mean(bin_errors["Bin 3 (Late 33%)"][ft]) if bin_errors["Bin 3 (Late 33%)"][ft] else float('nan')
        
        print(f"{ft:<30} | {b1_mae:12.2f} s | {b2_mae:12.2f} s | {b3_mae:12.2f} s")
        
    print("-" * 80)
    
    # Overall across all faults
    b1_all = [e for ft in all_faults for e in bin_errors["Bin 1 (Early 33%)"][ft]]
    b2_all = [e for ft in all_faults for e in bin_errors["Bin 2 (Mid 33%)"][ft]]
    b3_all = [e for ft in all_faults for e in bin_errors["Bin 3 (Late 33%)"][ft]]
    
    print(f"{'OVERALL AVERAGE':<30} | {np.mean(b1_all):12.2f} s | {np.mean(b2_all):12.2f} s | {np.mean(b3_all):12.2f} s")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
