"""
shap_analysis.py

Performs SHAP (SHapley Additive exPlanations) analysis on the trained 1D CNN RUL model:
1. Loads trained model and scaler weights (rul_model.pt).
2. Extracts post-detection test windows across major fault types (oil_pressure, misfire, overheating, alternator, combustion_instability).
3. Uses GradientExplainer to compute SHAP feature importance.
4. Confirms signature features drive predictions for each fault type.
5. Saves summary bar plots of feature importance (shap_summary.png).
"""

import os
import sys
import random
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from collections import defaultdict
import shap

# Add sys.path
sys.path.insert(0, os.path.dirname(__file__))
from train_rul_model import RULConvNet, WINDOW_SIZE, SEED

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../engine_simulation/data/dataset"))
MODEL_PATH = os.path.join(os.path.dirname(__file__), "rul_model.pt")
OUTPUT_DIR = os.path.dirname(__file__)

class ModelWrapper(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model
    def forward(self, x):
        out = self.model(x)
        if out.dim() == 1:
            out = out.unsqueeze(-1)
        return out

def get_test_missions():
    random.seed(SEED)
    summary_df = pd.read_csv(os.path.join(DATASET_DIR, "rul_summary.csv"))
    valid_missions = summary_df[summary_df["excluded_reason"].isnull() | (summary_df["excluded_reason"] == "")]
    mission_ids = valid_missions["mission_id"].tolist()
    random.shuffle(mission_ids)
    n = len(mission_ids)
    test_ids = mission_ids[int(n * 0.85):]
    fault_types = dict(zip(valid_missions["mission_id"], valid_missions["fault_type"]))
    return test_ids, fault_types

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device for SHAP: {device}")
    
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}")
        return
        
    checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=False)
    features = checkpoint['features']
    scaler_mean = checkpoint['scaler_mean']
    scaler_scale = checkpoint['scaler_scale']
    
    raw_model = RULConvNet(in_channels=len(features)).to(device)
    raw_model.load_state_dict(checkpoint['model_state_dict'])
    raw_model.eval()
    
    model = ModelWrapper(raw_model).to(device)
    
    test_ids, fault_types = get_test_missions()
    first_det_df = pd.read_csv(os.path.join(DATASET_DIR, "first_detections.csv"))
    det_map = dict(zip(first_det_df["mission_id"], first_det_df["t_first_detected"]))
    labels_df = pd.read_csv(os.path.join(DATASET_DIR, "rul_labels.csv"))
    
    fault_windows = defaultdict(list)
    background_windows = []
    
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
        x_scaled = (x_raw - scaler_mean) / scaler_scale
        
        # Sample windows evenly across the post-detection duration
        num_w = len(x_scaled) - WINDOW_SIZE + 1
        step = max(1, num_w // 20) # ~20 windows per test mission
        
        for i in range(0, num_w, step):
            w = x_scaled[i:i + WINDOW_SIZE, :]
            fault_windows[ft].append(w)
            if len(background_windows) < 100:
                background_windows.append(w)
                
    # Prepare background tensor
    bg_tensor = torch.tensor(np.array(background_windows[:100]), dtype=torch.float32).transpose(1, 2).to(device)
    explainer = shap.GradientExplainer(model, bg_tensor)
    
    print("Computing SHAP values for test samples per fault type...")
    
    fault_shap_results = {}
    
    for ft, windows in fault_windows.items():
        if not windows:
            continue
        test_tensor = torch.tensor(np.array(windows[:50]), dtype=torch.float32).transpose(1, 2).to(device)
        shap_vals = explainer.shap_values(test_tensor) # (N, features, window_len, 1)
        shap_arr = np.squeeze(shap_vals, axis=-1)       # (N, features, window_len)
        
        # Average absolute SHAP value across samples and time steps per feature
        mean_importance = np.mean(np.abs(shap_arr), axis=(0, 2))
        fault_shap_results[ft] = mean_importance
        
    print("\n" + "="*80)
    print("TOP SHAP FEATURE IMPORTANCES PER FAULT TYPE")
    print("="*80)
    
    target_faults = ["oil_pressure_fault", "misfire_fault", "overheating_fault", "alternator_fault", "combustion_instability_fault"]
    
    for ft in target_faults:
        if ft not in fault_shap_results:
            continue
        imp = fault_shap_results[ft]
        ranked_indices = np.argsort(imp)[::-1]
        
        print(f"\nFault Type: {ft.upper()}")
        print("-" * 50)
        for rank, idx in enumerate(ranked_indices[:5], 1):
            feat_name = features[idx]
            score = imp[idx]
            print(f"  {rank}. {feat_name:<30} | SHAP Score: {score:.5f}")
            
    print("="*80 + "\n")
    
    # 4. Generate SHAP Summary Bar Plot
    fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    plot_target_faults = ["oil_pressure_fault", "misfire_fault", "overheating_fault"]
    titles = ["Oil Pressure Fault Signature", "Misfire Fault Signature", "Overheating Fault Signature"]
    
    for i, ft in enumerate(plot_target_faults):
        ax = axes[i]
        if ft in fault_shap_results:
            imp = fault_shap_results[ft]
            ranked_indices = np.argsort(imp)[::-1][:8]
            top_feats = [features[j] for j in ranked_indices][::-1]
            top_scores = [imp[j] for j in ranked_indices][::-1]
            
            bars = ax.barh(top_feats, top_scores, color="crimson" if i==0 else ("navy" if i==1 else "darkorange"))
            ax.set_title(f"Top Features for {titles[i]} ({ft})")
            ax.set_xlabel("Mean |SHAP Value| (Impact on RUL Prediction)")
            ax.grid(True, linestyle="--", alpha=0.5)
            
    plt.tight_layout()
    plot_path = os.path.join(OUTPUT_DIR, "shap_summary.png")
    plt.savefig(plot_path)
    plt.close()
    print(f"Saved SHAP summary plot to {plot_path}")

if __name__ == "__main__":
    main()
