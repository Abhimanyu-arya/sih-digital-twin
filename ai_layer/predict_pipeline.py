"""
predict_pipeline.py

End-to-end live inference pipeline:
1. Receives streaming telemetry row-by-row.
2. Runs residual anomaly detector (process_timestamp).
3. If no sustained anomaly is detected: Outputs "NOMINAL - no active degradation, RUL not applicable".
4. Once an anomaly IS flagged: Switches to DEGRADED mode, extracts sliding window of features, and runs the 1D CNN RUL model.
"""

import os
import sys
import argparse
import math
import numpy as np
import pandas as pd
import torch
from collections import deque

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai_layer.anomaly_detection.residual_detector import process_timestamp
from ai_layer.rul_estimation.train_rul_model import RULConvNet, WINDOW_SIZE

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../engine_simulation/data/dataset"))
MODEL_PATH = os.path.join(os.path.dirname(__file__), "rul_estimation/rul_model.pt")

class LivePredictor:
    def __init__(self, model_path=MODEL_PATH):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model checkpoint not found at {model_path}")
            
        checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
        self.features = checkpoint['features']
        self.scaler_mean = checkpoint['scaler_mean']
        self.scaler_scale = checkpoint['scaler_scale']
        
        self.model = RULConvNet(in_channels=len(self.features)).to(self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        self.history = {}
        self.raw_window = deque(maxlen=WINDOW_SIZE)
        self.anomaly_detected = False
        self.anomaly_streak = 0
        self.t_detected = None

    def process_telemetry(self, row_dict):
        timestamp = row_dict['timestamp']
        
        # 1. Run Anomaly Detector
        res = process_timestamp(row_dict, self.history)
        any_anom = any(c['is_anomaly'] for c in res['channels'].values())
        
        if any_anom:
            self.anomaly_streak += 1
        else:
            self.anomaly_streak = 0
            
        if not self.anomaly_detected and self.anomaly_streak >= 3:
            self.anomaly_detected = True
            self.t_detected = timestamp
            
        # 2. Build feature vector for RUL model
        # Compute residuals manually or pull if precomputed
        rpm_cmd = row_dict.get('commanded_rpm', row_dict['rpm'])
        from engine_simulation.engine_simulator import steady_state_engine, NOISE_STD
        baseline = steady_state_engine(rpm=rpm_cmd, altitude_m=row_dict['altitude_m'])
        
        feat_vector = []
        # Raw features
        for f in ["rpm", "cht_c", "egt_c", "oil_pressure_bar", "oil_temp_c", "fuel_flow_lph", "vibration_g", "alternator_v", "injection_timing_deg", "altitude_m", "commanded_rpm"]:
            feat_vector.append(row_dict.get(f, 0.0))
            
        # Residual features
        for ch in ["cht_c", "egt_c", "oil_pressure_bar", "oil_temp_c", "fuel_flow_lph", "vibration_g", "alternator_v", "injection_timing_deg", "rpm"]:
            actual = row_dict.get(ch, 0.0)
            expected = baseline.get(ch, actual)
            residual = actual - expected
            z_score = residual / NOISE_STD.get(ch, 1.0)
            feat_vector.append(residual)
            feat_vector.append(z_score)
            
        t_elapsed = (timestamp - self.t_detected) if self.anomaly_detected and self.t_detected is not None else 0.0
        feat_vector.append(t_elapsed)
        
        feat_vector = np.array(feat_vector)
        # Scale
        feat_scaled = (feat_vector - self.scaler_mean) / self.scaler_scale
        self.raw_window.append(feat_scaled)
        
        # 3. Decision Logic
        if not self.anomaly_detected:
            return {
                "timestamp": timestamp,
                "status": "NOMINAL",
                "message": "NOMINAL - no active degradation, RUL not applicable",
                "rul_seconds": None
            }
        else:
            if len(self.raw_window) < WINDOW_SIZE:
                return {
                    "timestamp": timestamp,
                    "status": "DEGRADED_INITIALIZING",
                    "message": f"DEGRADED - Anomaly detected at t={self.t_detected}s. Warming up window ({len(self.raw_window)}/{WINDOW_SIZE}s)...",
                    "rul_seconds": None
                }
            
            # Predict RUL
            window_arr = np.array(self.raw_window) # (60, num_features)
            tensor_in = torch.tensor(window_arr, dtype=torch.float32).unsqueeze(0).transpose(1, 2).to(self.device)
            
            if getattr(self, 'is_latched', False):
                pred_rul = 0.0
            else:
                with torch.no_grad():
                    pred_log = self.model(tensor_in).cpu().item()
                pred_rul = math.expm1(pred_log)
                pred_rul = max(0.0, pred_rul)
                if pred_rul <= 5.0:
                    self.is_latched = True
                    pred_rul = 0.0
            
            severity_str = "CRITICAL" if pred_rul < 60 else "DEGRADED"
            
            return {
                "timestamp": timestamp,
                "status": severity_str,
                "message": f"{severity_str} - Active degradation detected! Estimated RUL: {pred_rul:.1f} seconds",
                "rul_seconds": round(pred_rul, 1)
            }


def main():
    parser = argparse.ArgumentParser(description="Live Digital Twin Predict Pipeline")
    parser.add_argument("--mission", default="mission_006", help="Mission ID to simulate")
    args = parser.parse_args()
    
    mid = args.mission
    csv_path = os.path.join(DATASET_DIR, f"{mid}.csv")
    if not os.path.exists(csv_path):
        print(f"File {csv_path} not found.")
        return
        
    df = pd.read_csv(csv_path)
    predictor = LivePredictor()
    
    print(f"Simulating Live Pipeline for {mid} ({len(df)} seconds total)...\n")
    
    results = []
    for _, row in df.iterrows():
        res = predictor.process_telemetry(row.to_dict())
        results.append(res)
        
    # Sample 3 key timestamps: pre-detection, just after detection, near failure
    det_timestamps = [r['timestamp'] for r in results if r['status'] in ['DEGRADED', 'CRITICAL']]
    
    # 1. Pre-detection
    t_pre = 100
    res_pre = next((r for r in results if r['timestamp'] == t_pre), results[0])
    
    # 2. Just after detection
    if det_timestamps:
        t_post_det = det_timestamps[0] + 60 # 60s after detection when window is full
        res_post_det = next((r for r in results if r['timestamp'] == t_post_det), results[-1])
    else:
        res_post_det = results[len(results)//2]
        
    # 3. Near failure
    t_fail = results[-1]['timestamp'] - 10
    res_fail = next((r for r in results if r['timestamp'] == t_fail), results[-1])
    
    print("="*80)
    print("SAMPLE PIPELINE OUTPUTS AT 3 KEY TIMESTAMPS:")
    print("="*80)
    print(f"\n1. PRE-DETECTION (t = {res_pre['timestamp']}s):")
    print(f"   Output: {res_pre['message']}")
    
    print(f"\n2. JUST AFTER DETECTION (t = {res_post_det['timestamp']}s):")
    print(f"   Output: {res_post_det['message']}")
    
    print(f"\n3. NEAR FAILURE (t = {res_fail['timestamp']}s):")
    print(f"   Output: {res_fail['message']}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
