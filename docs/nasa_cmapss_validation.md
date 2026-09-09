# NASA C-MAPSS FD001 Validation

This document records a validation exercise applying the same 1D CNN RUL
architecture used for our Rotax 912 digital twin to the NASA C-MAPSS FD001
turbofan degradation dataset. The purpose is to demonstrate that our
modeling *approach* produces competitive results on a standard, published
benchmark — independent of engine type.

This is a methodological validation, not a replacement for the Rotax-specific
model. The numbers below should be reported as-is.

## Dataset

| Property | Value |
|---|---|
| Dataset | NASA C-MAPSS FD001 (Saxena et al., PHM08) |
| Training trajectories | 100 engines (run-to-failure) |
| Test trajectories | 100 engines (truncated before failure) |
| Operating conditions | 1 (sea level) |
| Fault mode | 1 (HPC degradation) |
| Features used | 24 (3 operational settings + 21 sensor measurements) |
| Ground truth | `RUL_FD001.txt` (one true RUL value per test engine) |

## Methodology

The evaluation follows the standard C-MAPSS protocol used in published
literature. Key decisions:

1. **RUL capping at 125 cycles.** During training, the target RUL is
   clipped to a maximum of 125 cycles (the piecewise-linear degradation
   assumption). This is the standard practice in virtually all published
   C-MAPSS work — RUL values above 125 are not physically meaningful for
   degradation modeling since the engine is still in its healthy operating
   regime.

2. **Official final-cycle evaluation.** Test RMSE/MAE is computed using
   **one prediction per engine** at the **final available cycle** of each
   test trajectory, compared against the uncapped ground-truth values in
   `RUL_FD001.txt`. This is the standard protocol; it is *not* the same
   as per-timestep MAE across all rows (which would not be comparable to
   published benchmarks).

3. **Feature scaling.** StandardScaler fitted on training data only.
   Applied to train, validation, and test sets.

4. **Train/val split.** 80/20 by engine ID (80 train, 20 validation).

5. **Architecture.** Identical 3-layer 1D ConvNet to the Rotax model:
   Conv1d(32) → Conv1d(64) → Conv1d(128) → AdaptiveAvgPool → FC(64) → FC(1).
   Dropout 0.3. Adam optimizer, ReduceLROnPlateau scheduler. Early stopping
   with patience 12.

## Results

### Overall metrics (official protocol)

| Metric | Value (cycles) |
|---|---|
| **MAE** | **15.00** |
| **RMSE** | **19.31** |
| Test engines | 100 |
| Epochs trained | 35 (early-stopped at 23 patience) |

### MAE by proximity to failure

| True RUL Bin | N | MAE | RMSE |
|---|---|---|---|
| RUL < 20 (near failure) | 13 | 4.58 | 7.01 |
| 20 ≤ RUL < 50 | 17 | 13.72 | 17.48 |
| 50 ≤ RUL < 80 | 15 | 26.04 | 28.50 |
| 80 ≤ RUL < 125 | 44 | 12.40 | 16.09 |
| RUL ≥ 125 (early life) | 11 | 24.68 | 26.76 |

**Note on the RUL ≥ 125 bin:** These 11 engines have genuine uncapped
true RUL values of 126–145 in `RUL_FD001.txt`. The model was trained
with a 125-cycle cap, so it structurally cannot predict above ~125,
creating a minimum error floor of (true_rul − 125) for these engines.
This is inherent to the standard protocol, not a bug in our evaluation.

## Honest benchmark comparison

| Model class | Typical FD001 RMSE | Source |
|---|---|---|
| Strong (LSTM, DA-RNN, transformer) | ~12–18 | Li et al. 2018, Song et al. 2018 |
| Moderate (vanilla CNN, MLP) | ~18–25 | Sateesh Babu et al. 2016, Li et al. 2018 |
| Simpler baselines (SVR, RF) | ~25–40 | Various |
| **Our 1D CNN** | **19.31** | This work |

**Assessment:** Our RMSE of 19.31 falls in the moderate vanilla CNN/MLP
tier. It is a legitimate result for a simple 3-layer ConvNet without
attention mechanisms, multi-head architectures, or pre-training — but it
is not state-of-the-art. Published strong models achieve RMSE in the
12–18 range. We are above that ceiling but well below simpler baselines.

The fair characterization for the report: *"competitive with published
vanilla CNN baselines on FD001, though below state-of-the-art recurrent
and attention-based architectures."*

## Near-failure accuracy pattern

Both the Rotax and C-MAPSS models show the same "more accurate near
failure" behavior:

| Model | MAE near failure | MAE early life | Ratio |
|---|---|---|---|
| C-MAPSS (RUL < 20 vs ≥ 125) | 4.58 | 24.68 | ~5.4× better near failure |
| Rotax (post-detection, same architecture) | Lower MAE near EOL | Higher MAE early in degradation | Same pattern |

This consistency is expected — degradation signatures become increasingly
distinctive as engines approach failure, regardless of engine type. The
same 1D CNN architecture captures this pattern on both a proprietary
Rotax simulation dataset and a standard NASA turbofan benchmark.

This validates the *approach* (architecture + training methodology),
not just the dataset.

## Files

| File | Purpose |
|---|---|
| `ai_layer/rul_estimation/train_cmapss_fd001.py` | Training and official evaluation script |
| `ai_layer/rul_estimation/diagnose_rul_bins.py` | Diagnostic script verifying per-engine predictions |
| `ai_layer/rul_estimation/rul_cmapss_fd001.pt` | Saved model checkpoint |
| `Nasa-Cmapss/train_FD001.txt` | C-MAPSS training data |
| `Nasa-Cmapss/test_FD001.txt` | C-MAPSS test data |
| `Nasa-Cmapss/RUL_FD001.txt` | Ground-truth RUL values |

## Reference

Saxena, A., Goebel, K., Simon, D., and Eklund, N., "Damage Propagation
Modeling for Aircraft Engine Run-to-Failure Simulation", Proceedings of
the 1st International Conference on Prognostics and Health Management
(PHM08), Denver CO, October 2008.
