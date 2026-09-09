#!/usr/bin/env python
"""
train_cmapss_fd001.py

Trains a 1D CNN for Remaining Useful Life (RUL) estimation on NASA C-MAPSS FD001.

Follows the STANDARD C-MAPSS evaluation protocol used in published literature:
  - Training RUL is clipped at R_MAX = 125 cycles (piecewise-linear degradation).
  - Test evaluation uses ONE prediction per engine at its FINAL available cycle,
    compared against the ground-truth values in RUL_FD001.txt.

Architecture mirrors the Rotax model in train_rul_model.py (1D ConvNet).

Reference: Saxena et al., "Damage Propagation Modeling for Aircraft Engine
Run-to-Failure Simulation", PHM08, 2008.
"""

import os
import time
import math
import random
import numpy as np
import pandas as pd
from collections import defaultdict

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

# ---------------------------------------------------------------
# Hyperparameters
# ---------------------------------------------------------------
WINDOW_SIZE = 30       # cycles per sliding window (FD001 engines ~200 cycles avg)
BATCH_SIZE = 256
EPOCHS = 80
PATIENCE = 12
LEARNING_RATE = 1e-3
R_MAX = 125            # standard piecewise-linear RUL cap (cycles)

# ---------------------------------------------------------------
# Paths
# ---------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATASET_ROOT = os.path.join(BASE_DIR, "Nasa-Cmapss")
TRAIN_FILE = os.path.join(DATASET_ROOT, "train_FD001.txt")
TEST_FILE = os.path.join(DATASET_ROOT, "test_FD001.txt")
RUL_FILE = os.path.join(DATASET_ROOT, "RUL_FD001.txt")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "rul_cmapss_fd001.pt")


# ---------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------
def load_cmapss_train(file_path, r_max=R_MAX):
    """Load the C-MAPSS training file.

    Computes RUL = max_cycle - current_cycle, then clips to *r_max* (the
    standard piecewise-linear degradation assumption).
    """
    df = pd.read_csv(file_path, sep=r'\s+', header=None)
    # Columns: 0=engine_id, 1=cycle, 2-4=op_settings, 5-25=sensors
    # We keep op_settings (3) + sensors (21) = 24 feature columns
    n_cols = df.shape[1]
    op_cols = [f"op{i}" for i in range(1, 4)]
    sensor_cols = [f"s{i}" for i in range(1, n_cols - 4)]  # remaining columns
    df.columns = ["engine_id", "cycle"] + op_cols + sensor_cols
    feature_cols = op_cols + sensor_cols

    # Compute and CAP RUL
    max_cycle = df.groupby("engine_id")["cycle"].transform("max")
    df["rul"] = (max_cycle - df["cycle"]).clip(upper=r_max)

    return df, feature_cols


def load_cmapss_test(test_path, rul_path):
    """Load the C-MAPSS test file and attach ground-truth RUL from the RUL file.

    For official evaluation we only need the LAST window per engine, but we
    load the full trajectory so we can build windows up to (and ending at)
    the final cycle.
    """
    df = pd.read_csv(test_path, sep=r'\s+', header=None)
    n_cols = df.shape[1]
    op_cols = [f"op{i}" for i in range(1, 4)]
    sensor_cols = [f"s{i}" for i in range(1, n_cols - 4)]
    df.columns = ["engine_id", "cycle"] + op_cols + sensor_cols

    # Ground-truth RUL per engine (one value per engine, at the final cycle)
    true_rul = pd.read_csv(rul_path, header=None).squeeze().values  # shape (100,)

    # Map engine_id -> true_rul (engine_ids are 1-indexed and sequential)
    engine_ids_sorted = sorted(df["engine_id"].unique())
    rul_map = dict(zip(engine_ids_sorted, true_rul))

    # Per-row RUL = true_rul_at_final + (max_cycle - current_cycle)
    max_cycle = df.groupby("engine_id")["cycle"].transform("max")
    df["true_rul_final"] = df["engine_id"].map(rul_map)
    df["rul"] = df["true_rul_final"] + (max_cycle - df["cycle"])

    return df, op_cols + sensor_cols, rul_map


# ---------------------------------------------------------------
# Dataset / Model
# ---------------------------------------------------------------
class RULDataset(Dataset):
    def __init__(self, windows, targets):
        self.windows = torch.from_numpy(np.array(windows, dtype=np.float32))
        self.windows = self.windows.transpose(1, 2)  # (B, C, L) for Conv1D
        self.targets = torch.from_numpy(np.array(targets, dtype=np.float32))

    def __len__(self):
        return len(self.targets)

    def __getitem__(self, idx):
        return self.windows[idx], self.targets[idx]


class RULConvNet(nn.Module):
    """Same 3-layer 1D ConvNet as the Rotax RUL model."""
    def __init__(self, in_channels):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        self.relu = nn.ReLU()
        self.pool = nn.MaxPool1d(2)
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        self.dropout = nn.Dropout(0.3)
        self.fc1 = nn.Linear(128, 64)
        self.fc2 = nn.Linear(64, 1)

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.pool(x)
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        x = self.relu(self.conv3(x))
        x = self.global_pool(x).squeeze(-1)
        x = self.dropout(x)
        x = self.relu(self.fc1(x))
        return self.fc2(x).squeeze(-1)


# ---------------------------------------------------------------
# Window extraction
# ---------------------------------------------------------------
def extract_windows_per_engine(df, feature_cols, window_size=WINDOW_SIZE):
    """Sliding windows grouped by engine_id.

    Returns lists of (window, target_rul) tuples.
    """
    all_windows, all_targets = [], []
    for eid, grp in df.groupby("engine_id"):
        grp = grp.sort_values("cycle")
        data = grp[feature_cols].values
        rul = grp["rul"].values
        if len(grp) < window_size:
            continue
        for i in range(len(grp) - window_size + 1):
            all_windows.append(data[i:i + window_size])
            all_targets.append(rul[i + window_size - 1])
    return all_windows, all_targets


def extract_last_window_per_engine(df, feature_cols, window_size=WINDOW_SIZE):
    """Extract ONLY the final window per engine (for official test evaluation).

    Returns: windows list, engine_ids list (parallel).
    """
    windows, engine_ids = [], []
    for eid, grp in df.groupby("engine_id"):
        grp = grp.sort_values("cycle")
        data = grp[feature_cols].values
        if len(grp) < window_size:
            # Pad with first-row repetition if trajectory is shorter than window
            pad_len = window_size - len(grp)
            data = np.vstack([np.tile(data[0], (pad_len, 1)), data])
        window = data[-window_size:]  # last WINDOW_SIZE cycles
        windows.append(window)
        engine_ids.append(eid)
    return windows, engine_ids


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------
def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # ===========================================================
    # 1. Load data
    # ===========================================================
    print("Loading C-MAPSS FD001 data...")
    train_df, feature_cols = load_cmapss_train(TRAIN_FILE)
    test_df, _, rul_map = load_cmapss_test(TEST_FILE, RUL_FILE)

    print(f"  Training engines: {train_df['engine_id'].nunique()}")
    print(f"  Test engines:     {test_df['engine_id'].nunique()}")
    print(f"  Features:         {len(feature_cols)}")
    print(f"  RUL cap (R_MAX):  {R_MAX} cycles")

    # ===========================================================
    # 2. Train / Validation split (80/20 by engine)
    # ===========================================================
    engine_ids = list(train_df["engine_id"].unique())
    random.shuffle(engine_ids)
    split = int(0.8 * len(engine_ids))
    train_ids = set(engine_ids[:split])
    val_ids = set(engine_ids[split:])

    train_sub = train_df[train_df["engine_id"].isin(train_ids)].copy()
    val_sub = train_df[train_df["engine_id"].isin(val_ids)].copy()
    print(f"  Train/Val split:  {len(train_ids)} / {len(val_ids)} engines")

    # ===========================================================
    # 3. Feature scaling (fit on train only)
    # ===========================================================
    # Cast feature columns to float to avoid int->float assignment errors
    for col in feature_cols:
        train_sub[col] = train_sub[col].astype(np.float64)
        val_sub[col] = val_sub[col].astype(np.float64)
        test_df[col] = test_df[col].astype(np.float64)

    scaler = StandardScaler()
    scaler.fit(train_sub[feature_cols])

    train_sub[feature_cols] = scaler.transform(train_sub[feature_cols])
    val_sub[feature_cols] = scaler.transform(val_sub[feature_cols])
    test_df[feature_cols] = scaler.transform(test_df[feature_cols])

    # ===========================================================
    # 4. Build sliding windows (train & val use all windows)
    # ===========================================================
    print("Building sliding windows...")
    train_w, train_t = extract_windows_per_engine(train_sub, feature_cols)
    val_w, val_t = extract_windows_per_engine(val_sub, feature_cols)

    train_ds = RULDataset(train_w, train_t)
    val_ds = RULDataset(val_w, val_t)

    print(f"  Train windows: {len(train_ds)}, Val windows: {len(val_ds)}")

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

    # ===========================================================
    # 5. Model
    # ===========================================================
    model = RULConvNet(in_channels=len(feature_cols)).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=4, factor=0.5)

    # ===========================================================
    # 6. Training loop
    # ===========================================================
    print("\nTraining...")
    best_val = float("inf")
    patience_ctr = 0
    t_start = time.time()

    for epoch in range(1, EPOCHS + 1):
        # --- Train ---
        model.train()
        train_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * xb.size(0)
        train_loss /= len(train_ds)

        # --- Validate ---
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                val_loss += criterion(model(xb), yb).item() * xb.size(0)
        val_loss /= len(val_ds)

        scheduler.step(val_loss)

        print(f"  Epoch {epoch:03d}/{EPOCHS} | Train MSE: {train_loss:.4f} | Val MSE: {val_loss:.4f}")

        if val_loss < best_val:
            best_val = val_loss
            patience_ctr = 0
            torch.save({
                "model_state_dict": model.state_dict(),
                "scaler_mean": scaler.mean_,
                "scaler_scale": scaler.scale_,
                "feature_cols": feature_cols,
                "r_max": R_MAX,
                "window_size": WINDOW_SIZE,
            }, MODEL_PATH)
        else:
            patience_ctr += 1
            if patience_ctr >= PATIENCE:
                print(f"  Early stopping after {epoch} epochs.")
                break

    print(f"Training finished in {time.time() - t_start:.1f}s\n")

    # ===========================================================
    # 7. OFFICIAL C-MAPSS TEST EVALUATION
    #    One prediction per engine at its final available cycle,
    #    compared to RUL_FD001.txt ground truth.
    # ===========================================================
    print("=" * 60)
    print("OFFICIAL C-MAPSS FD001 TEST EVALUATION")
    print("  Protocol: 1 prediction per engine at final cycle")
    print("  Ground truth: RUL_FD001.txt")
    print("  RUL cap during training: %d cycles" % R_MAX)
    print("=" * 60)

    checkpoint = torch.load(MODEL_PATH, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    # Extract the LAST window for each test engine
    test_windows, test_eids = extract_last_window_per_engine(test_df, feature_cols)
    test_windows_np = np.array(test_windows, dtype=np.float32)
    test_tensor = torch.from_numpy(test_windows_np).transpose(1, 2).to(device)

    with torch.no_grad():
        preds = model(test_tensor).cpu().numpy()  # predicted RUL (cycles)

    # Ground-truth RUL for each engine (from RUL_FD001.txt)
    true_rul = np.array([rul_map[eid] for eid in test_eids], dtype=np.float64)
    pred_rul = preds.astype(np.float64)

    # Clip predictions to [0, inf) -- can't have negative RUL
    pred_rul = np.maximum(pred_rul, 0.0)

    errors = pred_rul - true_rul
    abs_errors = np.abs(errors)

    overall_mae = np.mean(abs_errors)
    overall_rmse = np.sqrt(np.mean(errors ** 2))

    print(f"\n  Test engines:  {len(test_eids)}")
    print(f"  Overall MAE:   {overall_mae:.2f} cycles")
    print(f"  Overall RMSE:  {overall_rmse:.2f} cycles")

    # ----------------------------------------------------------
    # Breakdown by proximity to failure
    # ----------------------------------------------------------
    print("\n  MAE by proximity to failure (true RUL bins):")
    bins = [
        ("RUL < 20 (near failure)", lambda r: r < 20),
        ("20 <= RUL < 50",         lambda r: (r >= 20) & (r < 50)),
        ("50 <= RUL < 80",         lambda r: (r >= 50) & (r < 80)),
        ("80 <= RUL < 125",        lambda r: (r >= 80) & (r < 125)),
        ("RUL >= 125 (early life)",lambda r: r >= 125),
    ]
    for label, cond in bins:
        mask = cond(true_rul)
        n = mask.sum()
        if n > 0:
            bin_mae = np.mean(abs_errors[mask])
            bin_rmse = np.sqrt(np.mean(errors[mask] ** 2))
            print(f"    {label:30s}  N={n:3d}  MAE={bin_mae:6.2f}  RMSE={bin_rmse:6.2f}")
        else:
            print(f"    {label:30s}  N=  0  (no engines in this bin)")

    # ----------------------------------------------------------
    # Comparison context for the report
    # ----------------------------------------------------------
    print("\n" + "=" * 60)
    print("BENCHMARK CONTEXT (FD001 published results):")
    print("  Strong models (LSTM, DA-RNN, etc.):  RMSE ~12-18")
    print("  Moderate models (vanilla CNN, MLP):   RMSE ~18-25")
    print("  Simpler baselines (SVR, RF):          RMSE ~25-40")
    print("  Our 1D CNN result:                    RMSE = %.2f" % overall_rmse)
    print("=" * 60)


if __name__ == "__main__":
    main()
