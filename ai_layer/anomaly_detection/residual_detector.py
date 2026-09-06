import sys
import os
import argparse
import json
import numpy as np
import pandas as pd
from collections import deque

# Add project root to path to import engine_simulation module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from engine_simulation.engine_simulator import steady_state_engine, NOISE_STD

MAGNITUDE_Z_THRESHOLD = 3.0
TREND_WINDOW_SIZE = 60
TREND_Z_SLOPE_THRESHOLD = 0.02  # Equivalent to drifting 1.2 z-scores over 60 seconds

def process_timestamp(row_dict, history):
    """
    Process a single timestamp (row) of telemetry data.
    
    Args:
        row_dict (dict): A dictionary representing a single timestamp's sensor values.
        history (dict): A dictionary mapping channel names to a deque of their recent z-scores.
        
    Returns:
        dict: The anomaly detection results for this timestamp.
    """
    # 1. Compute baseline expected values
    rpm_cmd = row_dict.get('commanded_rpm', row_dict['rpm'])
    baseline = steady_state_engine(rpm=rpm_cmd, altitude_m=row_dict['altitude_m'])
    
    results = {
        'timestamp': row_dict['timestamp'],
        'channels': {}
    }
    
    # Also check rpm channel if commanded_rpm is present
    for channel, std in NOISE_STD.items():
        if channel in ['altitude_m', 'commanded_rpm']: 
            continue
        if channel == 'rpm' and 'commanded_rpm' not in row_dict:
            continue # If no commanded_rpm, rpm is independent variable
            
        if channel not in row_dict:
            continue
            
        actual = row_dict[channel]
        expected = baseline[channel]
        residual = actual - expected
        z_score = residual / std
        
        # update history
        if channel not in history:
            history[channel] = deque(maxlen=TREND_WINDOW_SIZE)
        history[channel].append(z_score)
        
        # Magnitude check
        mag_anomaly = abs(z_score) >= MAGNITUDE_Z_THRESHOLD
        
        # Trend check
        trend_anomaly = False
        if len(history[channel]) == TREND_WINDOW_SIZE:
            y = np.array(history[channel])
            x = np.arange(len(y))
            # Fit a linear regression (degree 1)
            slope, _ = np.polyfit(x, y, 1)
            
            # We want to catch consistent drifting away from 0.
            # If current z_score is positive, slope should be positive.
            # If current z_score is negative, slope should be negative.
            # We also ensure the z-score is at least somewhat anomalous (>1.0) 
            # to avoid triggering on pure healthy noise that happens to have a slope.
            if z_score > 1.0 and slope > TREND_Z_SLOPE_THRESHOLD:
                trend_anomaly = True
            elif z_score < -1.0 and slope < -TREND_Z_SLOPE_THRESHOLD:
                trend_anomaly = True
                
        # Determine trigger
        if mag_anomaly and trend_anomaly:
            trigger = 'both'
        elif mag_anomaly:
            trigger = 'magnitude'
        elif trend_anomaly:
            trigger = 'trend'
        else:
            trigger = 'none'
            
        is_anomaly = (trigger != 'none')
        
        results['channels'][channel] = {
            'raw_residual': residual,
            'z_score': z_score,
            'is_anomaly': is_anomaly,
            'trigger': trigger
        }
        
    return results

def main():
    parser = argparse.ArgumentParser(description="Residual-based anomaly detection")
    parser.add_argument("--input", required=True, help="Path to input mission CSV")
    parser.add_argument("--output", required=True, help="Path to output JSON")
    args = parser.parse_args()

    # Load data
    print(f"Loading data from {args.input}...")
    df = pd.read_csv(args.input)
    
    history = {}
    all_results = []
    
    print("Processing timestamps...")
    for index, row in df.iterrows():
        # Convert row to dict
        row_dict = row.to_dict()
        
        # Process the single timestamp
        res = process_timestamp(row_dict, history)
        
        # Also include fault label for easy evaluation/plotting later
        res['true_fault_label'] = row_dict.get('fault_label', 'none')
        
        all_results.append(res)
        
    # Save output
    print(f"Saving results to {args.output}...")
    with open(args.output, "w") as f:
        json.dump(all_results, f, indent=2)
    print("Done!")

if __name__ == "__main__":
    main()
