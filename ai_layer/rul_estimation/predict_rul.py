"""
predict_rul.py

Minimal inference script to demonstrate how to load the trained 1D CNN RUL model
and run prediction on a single 60-second window.
"""

import os
import sys
import numpy as np
import pandas as pd
import torch
import math

# We need the model definition
from train_rul_model import RULConvNet, WINDOW_SIZE

def predict_on_window(window_df, model_path="rul_model.pt"):
    """
    Predict RUL for a single 60-timestep dataframe window.
    window_df must have 60 rows and contain all required features.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}")
        return None
        
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    
    features = checkpoint['features']
    scaler_mean = checkpoint['scaler_mean']
    scaler_scale = checkpoint['scaler_scale']
    
    if len(window_df) != WINDOW_SIZE:
        print(f"Error: Expected window size {WINDOW_SIZE}, got {len(window_df)}")
        return None
        
    # Extract features in the correct order
    try:
        x_raw = window_df[features].values
    except KeyError as e:
        print(f"Error: Missing required features in window: {e}")
        return None
        
    # Scale features
    x_scaled = (x_raw - scaler_mean) / scaler_scale
    
    # Reshape for PyTorch CNN: (Batch, Channels, Length) -> (1, Channels, 60)
    x_tensor = torch.tensor(x_scaled, dtype=torch.float32).unsqueeze(0)
    x_tensor = x_tensor.transpose(1, 2).to(device)
    
    # Initialize and load model
    model = RULConvNet(in_channels=len(features)).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    with torch.no_grad():
        pred_log = model(x_tensor).item()
        
    # Inverse transform: exp(log_rul) - 1
    pred_real = math.expm1(pred_log)
    
    return pred_real

def main():
    # As a quick demonstration, we'll grab the last 60 rows of a random mission
    # that reached failure (e.g. oil_pressure_fault demo)
    
    demo_file = os.path.join(os.path.dirname(__file__), "../../engine_simulation/data/demo_mission_oil_pressure_fault.csv")
    
    if not os.path.exists(demo_file):
        print("Demo mission file not found for inference test.")
        return
        
    df = pd.read_csv(demo_file)
    
    # We need residual features for the demo mission as well.
    # We can compute them on the fly for the 60 rows.
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from engine_simulation.engine_simulator import steady_state_engine, NOISE_STD
    
    # Let's just grab the last 60 seconds
    window = df.tail(WINDOW_SIZE).copy()
    
    channels = [c for c in NOISE_STD.keys() if c not in ["rpm", "altitude_m", "commanded_rpm"]]
    
    # Compute residuals for window
    for idx, row in window.iterrows():
        baseline = steady_state_engine(rpm=row["commanded_rpm"], altitude_m=row["altitude_m"])
        for ch in channels:
            res = row[ch] - baseline[ch]
            z = res / NOISE_STD[ch]
            window.at[idx, f"{ch}_residual"] = res
            window.at[idx, f"{ch}_z"] = z
            
        # rpm residual
        res_rpm = row["rpm"] - baseline["rpm"]
        z_rpm = res_rpm / NOISE_STD["rpm"]
        window.at[idx, "rpm_residual"] = res_rpm
        window.at[idx, "rpm_z"] = z_rpm
        
    model_path = os.path.join(os.path.dirname(__file__), "rul_model.pt")
    
    print(f"Predicting RUL for the final 60 seconds of oil_pressure_fault demo...")
    prediction = predict_on_window(window, model_path)
    
    if prediction is not None:
        print(f"Predicted RUL: {prediction:.2f} seconds")
        print("(Since this is the very end of a faulted mission, RUL should be close to 0)")

if __name__ == "__main__":
    main()
