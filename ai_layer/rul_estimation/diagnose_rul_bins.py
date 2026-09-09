"""
Diagnostic: inspect the RUL>=125 bin to verify evaluation consistency.
Shows true RUL (from RUL_FD001.txt), capped training target, and model prediction
for each engine in that bin.
"""
import os, sys
import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler

# Reuse definitions from the training script
sys.path.insert(0, os.path.dirname(__file__))
from train_cmapss_fd001 import (
    RULConvNet, load_cmapss_train, load_cmapss_test,
    extract_last_window_per_engine, TRAIN_FILE, TEST_FILE, RUL_FILE,
    MODEL_PATH, R_MAX, WINDOW_SIZE, SEED
)
import random
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load data (same pipeline as training)
    train_df, feature_cols = load_cmapss_train(TRAIN_FILE)
    test_df, _, rul_map = load_cmapss_test(TEST_FILE, RUL_FILE)

    # Read raw RUL_FD001.txt to show uncapped ground truth
    raw_rul = pd.read_csv(RUL_FILE, header=None).squeeze().values
    engine_ids_sorted = sorted(test_df["engine_id"].unique())
    raw_rul_map = dict(zip(engine_ids_sorted, raw_rul))

    # Reproduce the exact scaler from training
    engine_ids_all = list(train_df["engine_id"].unique())
    random.shuffle(engine_ids_all)
    split = int(0.8 * len(engine_ids_all))
    train_ids = set(engine_ids_all[:split])
    train_sub = train_df[train_df["engine_id"].isin(train_ids)].copy()

    for col in feature_cols:
        train_sub[col] = train_sub[col].astype(np.float64)
        test_df[col] = test_df[col].astype(np.float64)

    scaler = StandardScaler()
    scaler.fit(train_sub[feature_cols])
    test_df[feature_cols] = scaler.transform(test_df[feature_cols])

    # Load model
    checkpoint = torch.load(MODEL_PATH, weights_only=False)
    model = RULConvNet(in_channels=len(feature_cols)).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    # Get final-cycle predictions
    test_windows, test_eids = extract_last_window_per_engine(test_df, feature_cols)
    test_tensor = torch.from_numpy(
        np.array(test_windows, dtype=np.float32)
    ).transpose(1, 2).to(device)

    with torch.no_grad():
        preds = model(test_tensor).cpu().numpy()
    preds = np.maximum(preds, 0.0)

    # Build comparison table
    print("=" * 72)
    print("FULL COMPARISON TABLE FOR ALL 100 TEST ENGINES")
    print("=" * 72)
    print(f"{'Engine':>7}  {'True RUL':>10}  {'Capped (train)':>14}  {'Predicted':>10}  {'Error':>8}  {'Bin':>20}")
    print("-" * 72)

    for i, eid in enumerate(test_eids):
        true_rul = raw_rul_map[eid]
        capped = min(true_rul, R_MAX)
        pred = preds[i]
        error = pred - true_rul

        if true_rul < 20:
            bin_label = "RUL < 20"
        elif true_rul < 50:
            bin_label = "20 <= RUL < 50"
        elif true_rul < 80:
            bin_label = "50 <= RUL < 80"
        elif true_rul < 125:
            bin_label = "80 <= RUL < 125"
        else:
            bin_label = "RUL >= 125 ***"

        print(f"{eid:>7}  {true_rul:>10}  {capped:>14}  {pred:>10.2f}  {error:>8.2f}  {bin_label:>20}")

    # Now focus on the RUL >= 125 bin
    print("\n" + "=" * 72)
    print("DETAIL: ENGINES IN THE RUL >= 125 BIN")
    print("=" * 72)
    print()
    print("Key question: Is the model comparing capped predictions against")
    print("uncapped ground truth, creating an artificial error floor?")
    print()
    print(f"{'Engine':>7}  {'True RUL':>10}  {'Train target':>12}  {'Predicted':>10}  {'Error':>8}")
    print("-" * 55)

    bin_engines = []
    for i, eid in enumerate(test_eids):
        true_rul = raw_rul_map[eid]
        if true_rul >= 125:
            capped = min(true_rul, R_MAX)
            pred = preds[i]
            error = pred - true_rul
            bin_engines.append((eid, true_rul, capped, pred, error))
            print(f"{eid:>7}  {true_rul:>10}  {capped:>12}  {pred:>10.2f}  {error:>8.2f}")

    print()
    print(f"Engines in bin: {len(bin_engines)}")
    print()
    print("ANALYSIS:")
    print(f"  - Training capped RUL at {R_MAX}, so the model learned to predict [0, ~{R_MAX}].")
    print(f"  - Ground truth in RUL_FD001.txt is UNCAPPED (true remaining cycles).")
    print(f"  - For engines with true RUL > {R_MAX}, the model is structurally limited")
    print(f"    to predicting ~{R_MAX} at best, creating a minimum error floor of")
    print(f"    (true_rul - {R_MAX}) for those engines.")
    print()

    true_ruls = [e[1] for e in bin_engines]
    preds_bin = [e[3] for e in bin_engines]
    errors_bin = [e[4] for e in bin_engines]
    print(f"  True RUL range in this bin: {min(true_ruls)} - {max(true_ruls)}")
    print(f"  Predicted range:            {min(preds_bin):.2f} - {max(preds_bin):.2f}")
    print(f"  Mean absolute error:        {np.mean(np.abs(errors_bin)):.2f}")
    print()

    # What would the MAE be if we evaluated against CAPPED ground truth?
    capped_errors = [p - min(t, R_MAX) for p, t in zip(preds_bin, true_ruls)]
    print(f"  [Alternative] MAE vs CAPPED ground truth: {np.mean(np.abs(capped_errors)):.2f}")
    print(f"  (This is what you'd get if comparing apples-to-apples on capped scale)")

if __name__ == "__main__":
    main()
