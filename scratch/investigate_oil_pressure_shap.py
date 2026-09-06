"""
investigate_oil_pressure_shap.py

1. Prints full 30-feature SHAP ranking for oil_pressure_fault.
2. Checks post-detection variance and trajectory of oil_pressure_bar vs other channels.
3. Verifies feature indexing logic.
"""

import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai_layer.rul_estimation.train_rul_model import RULConvNet, WINDOW_SIZE, SEED, DATASET_DIR, MODEL_PATH
from ai_layer.rul_estimation.evaluate_rul_model import get_test_missions
import shap

class ModelWrapper(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model
    def forward(self, x):
        out = self.model(x)
        if out.dim() == 1:
            out = out.unsqueeze(-1)
        return out

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
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
    
    oil_windows = []
    bg_windows = []
    
    oil_post_det_dfs = []
    
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
            
        if ft == "oil_pressure_fault":
            oil_post_det_dfs.append(merged)
            
        x_raw = merged[features].values
        x_scaled = (x_raw - scaler_mean) / scaler_scale
        
        num_w = len(x_scaled) - WINDOW_SIZE + 1
        step = max(1, num_w // 20)
        
        for i in range(0, num_w, step):
            w = x_scaled[i:i + WINDOW_SIZE, :]
            if ft == "oil_pressure_fault":
                oil_windows.append(w)
            if len(bg_windows) < 100:
                bg_windows.append(w)
                
    bg_tensor = torch.tensor(np.array(bg_windows[:100]), dtype=torch.float32).transpose(1, 2).to(device)
    explainer = shap.GradientExplainer(model, bg_tensor)
    
    test_tensor = torch.tensor(np.array(oil_windows[:50]), dtype=torch.float32).transpose(1, 2).to(device)
    shap_vals = explainer.shap_values(test_tensor)
    shap_arr = np.squeeze(shap_vals, axis=-1)
    
    mean_imp = np.mean(np.abs(shap_arr), axis=(0, 2))
    ranked_indices = np.argsort(mean_imp)[::-1]
    
    print("\n" + "="*80)
    print("FULL 30-FEATURE SHAP RANKING FOR OIL_PRESSURE_FAULT")
    print("="*80)
    for rank, idx in enumerate(ranked_indices, 1):
        feat_name = features[idx]
        score = mean_imp[idx]
        is_target = " <<< TARGET SENSOR" if "oil_pressure" in feat_name else ""
        print(f"{rank:2d}. {feat_name:<32} | SHAP Score: {score:.6f}{is_target}")
    print("="*80 + "\n")
    
    # Analyze variance and trajectory of oil_pressure_bar vs oil_temp_c in post-detection window
    print("="*80)
    print("POST-DETECTION CHANNEL VARIANCE & TRAJECTORY ANALYSIS (Oil Pressure Faults)")
    print("="*80)
    concat_df = pd.concat(oil_post_det_dfs, ignore_index=True)
    
    channels_to_check = ["oil_pressure_bar", "oil_pressure_bar_residual", "oil_pressure_bar_z", 
                          "oil_temp_c", "oil_temp_c_residual", "oil_temp_c_z", "time_since_detection"]
    
    for ch in channels_to_check:
        vals = concat_df[ch].values
        print(f"Channel: {ch:<28} | Mean: {np.mean(vals):8.3f} | Std (StdDev): {np.std(vals):8.3f} | Min: {np.min(vals):8.3f} | Max: {np.max(vals):8.3f}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
