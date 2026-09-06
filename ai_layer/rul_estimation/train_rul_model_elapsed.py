"""
train_rul_model_elapsed.py

Retrains the gated 1D CNN RUL model with an additional feature: 'time_since_detection'
(elapsed time in seconds since the first anomaly detection).
"""

import os
import sys
import glob
import time
import math
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from collections import defaultdict
import random

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../engine_simulation/data/dataset"))
MODEL_PATH = os.path.join(os.path.dirname(__file__), "rul_model_elapsed.pt")

WINDOW_SIZE = 60
BATCH_SIZE = 256
EPOCHS = 100
PATIENCE = 10
LEARNING_RATE = 1e-3

RAW_FEATURES = ["rpm", "cht_c", "egt_c", "oil_pressure_bar", "oil_temp_c", "fuel_flow_lph", "vibration_g", "alternator_v", "injection_timing_deg", "altitude_m", "commanded_rpm"]
RESIDUAL_FEATURES = ["cht_c_residual", "cht_c_z", "egt_c_residual", "egt_c_z", "oil_pressure_bar_residual", "oil_pressure_bar_z", 
                     "oil_temp_c_residual", "oil_temp_c_z", "fuel_flow_lph_residual", "fuel_flow_lph_z", "vibration_g_residual", "vibration_g_z", 
                     "alternator_v_residual", "alternator_v_z", "injection_timing_deg_residual", "injection_timing_deg_z", "rpm_residual", "rpm_z"]
ELAPSED_FEATURE = ["time_since_detection"]

ALL_FEATURES = RAW_FEATURES + RESIDUAL_FEATURES + ELAPSED_FEATURE

class RULDataset(Dataset):
    def __init__(self, windows, targets, fault_types):
        self.windows = torch.tensor(np.array(windows), dtype=torch.float32)
        self.windows = self.windows.transpose(1, 2)
        self.targets = torch.tensor(targets, dtype=torch.float32)
        self.fault_types = fault_types
        
    def __len__(self):
        return len(self.targets)
        
    def __getitem__(self, idx):
        return self.windows[idx], self.targets[idx], self.fault_types[idx]

class RULConvNet(nn.Module):
    def __init__(self, in_channels):
        super(RULConvNet, self).__init__()
        self.conv1 = nn.Conv1d(in_channels, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        
        self.relu = nn.ReLU()
        self.pool = nn.MaxPool1d(2)
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        
        self.fc1 = nn.Linear(128, 64)
        self.fc2 = nn.Linear(64, 1)

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.pool(x)
        
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        
        x = self.relu(self.conv3(x))
        x = self.global_pool(x).squeeze(-1)
        
        x = self.relu(self.fc1(x))
        out = self.fc2(x)
        return out.squeeze(-1)

def extract_windows(df_group, fault_type):
    if len(df_group) < WINDOW_SIZE:
        return [], [], []
        
    features = df_group[ALL_FEATURES].values
    rul = df_group["rul_seconds"].values
    
    windows = []
    targets = []
    f_types = []
    
    for i in range(len(df_group) - WINDOW_SIZE + 1):
        window = features[i:i + WINDOW_SIZE, :]
        target_rul = rul[i + WINDOW_SIZE - 1]
        
        windows.append(window)
        targets.append(math.log1p(target_rul))
        f_types.append(fault_type)
        
    return windows, targets, f_types

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    print("Loading data...")
    summary_df = pd.read_csv(os.path.join(DATASET_DIR, "rul_summary.csv"))
    labels_df = pd.read_csv(os.path.join(DATASET_DIR, "rul_labels.csv"))
    first_det_df = pd.read_csv(os.path.join(DATASET_DIR, "first_detections.csv"))
    det_map = dict(zip(first_det_df["mission_id"], first_det_df["t_first_detected"]))
    
    valid_missions = summary_df[summary_df["excluded_reason"].isnull() | (summary_df["excluded_reason"] == "")]
    mission_ids = valid_missions["mission_id"].tolist()
    
    random.shuffle(mission_ids)
    
    n = len(mission_ids)
    train_ids = set(mission_ids[:int(n * 0.7)])
    val_ids = set(mission_ids[int(n * 0.7):int(n * 0.85)])
    test_ids = set(mission_ids[int(n * 0.85):])
    
    fault_type_map = dict(zip(valid_missions["mission_id"], valid_missions["fault_type"]))
    
    train_dfs, val_dfs, test_dfs = [], [], []
    
    for mid in mission_ids:
        raw_df = pd.read_csv(os.path.join(DATASET_DIR, f"{mid}.csv"))
        res_df = pd.read_csv(os.path.join(DATASET_DIR, f"residuals_{mid.replace('mission_', '')}.csv"))
        lbl_df = labels_df[labels_df["mission_id"] == mid]
        
        merged = pd.merge(raw_df, res_df, on="timestamp")
        merged = pd.merge(merged, lbl_df, on="timestamp")
        merged["fault_type"] = fault_type_map[mid]
        
        if mid in det_map and pd.notnull(det_map[mid]):
            t_det = det_map[mid]
            merged["time_since_detection"] = merged["timestamp"] - t_det
            merged = merged[merged["timestamp"] >= t_det].reset_index(drop=True)
        else:
            merged["time_since_detection"] = 0.0
            
        if len(merged) >= WINDOW_SIZE:
            if mid in train_ids:
                train_dfs.append(merged)
            elif mid in val_ids:
                val_dfs.append(merged)
            else:
                test_dfs.append(merged)
                
    scaler = StandardScaler()
    train_df = pd.concat(train_dfs, ignore_index=True)
    scaler.fit(train_df[ALL_FEATURES])
    
    for df in train_dfs:
        df[ALL_FEATURES] = scaler.transform(df[ALL_FEATURES])
    for df in val_dfs:
        df[ALL_FEATURES] = scaler.transform(df[ALL_FEATURES])
    for df in test_dfs:
        df[ALL_FEATURES] = scaler.transform(df[ALL_FEATURES])
        
    def build_dataset(dfs_list):
        windows, targets, fault_types = [], [], []
        for df in dfs_list:
            w, t, f = extract_windows(df, df["fault_type"].iloc[0])
            windows.extend(w)
            targets.extend(t)
            fault_types.extend(f)
        return RULDataset(windows, targets, fault_types)
        
    print("Building windows...")
    train_ds = build_dataset(train_dfs)
    val_ds = build_dataset(val_dfs)
    test_ds = build_dataset(test_dfs)
    
    print(f"Windows -> Train: {len(train_ds)}, Val: {len(val_ds)}, Test: {len(test_ds)}")
    
    def collate_fn(batch):
        x = torch.stack([item[0] for item in batch])
        y = torch.stack([item[1] for item in batch])
        ft = [item[2] for item in batch]
        return x, y, ft

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, collate_fn=collate_fn)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, collate_fn=collate_fn)
    
    model = RULConvNet(in_channels=len(ALL_FEATURES)).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    print("Starting training with time_since_detection feature...")
    start_time = time.time()
    
    best_val_loss = float('inf')
    patience_counter = 0
    
    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0.0
        for x_batch, y_batch, _ in train_loader:
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            preds = model(x_batch)
            loss = criterion(preds, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * x_batch.size(0)
            
        train_loss /= len(train_ds)
        
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x_batch, y_batch, _ in val_loader:
                x_batch, y_batch = x_batch.to(device), y_batch.to(device)
                preds = model(x_batch)
                loss = criterion(preds, y_batch)
                val_loss += loss.item() * x_batch.size(0)
                
        val_loss /= len(val_ds)
        print(f"Epoch {epoch+1:03d}/{EPOCHS:03d} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save({
                'model_state_dict': model.state_dict(),
                'scaler_mean': scaler.mean_,
                'scaler_scale': scaler.scale_,
                'features': ALL_FEATURES
            }, MODEL_PATH)
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                print(f"Early stopping triggered after {epoch+1} epochs.")
                break
                
    print(f"Training completed in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    main()
