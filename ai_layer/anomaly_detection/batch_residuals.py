"""
batch_residuals.py

Computes raw_residual and z_score features for all missions in the generated dataset.
Outputs to engine_simulation/data/dataset/residuals_*.csv
"""

import os
import sys
import glob
import pandas as pd

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from engine_simulation.engine_simulator import steady_state_engine, NOISE_STD

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../engine_simulation/data/dataset"))

def process_mission(csv_path):
    mission_id = os.path.basename(csv_path).replace("mission_", "").replace(".csv", "")
    out_path = os.path.join(DATASET_DIR, f"residuals_{mission_id}.csv")
    
    df = pd.read_csv(csv_path)
    
    residual_records = []
    
    channels = [c for c in NOISE_STD.keys() if c not in ["rpm", "altitude_m", "commanded_rpm"]]
    
    for _, row in df.iterrows():
        # Use commanded_rpm for baseline expectation
        baseline = steady_state_engine(rpm=row["commanded_rpm"], altitude_m=row["altitude_m"])
        
        record = {"timestamp": row["timestamp"]}
        
        for ch in channels:
            if ch not in row:
                continue
            actual = row[ch]
            expected = baseline[ch]
            residual = actual - expected
            z_score = residual / NOISE_STD[ch]
            
            record[f"{ch}_residual"] = residual
            record[f"{ch}_z"] = z_score
            
        # We also need residuals for rpm, wait, NOISE_STD has 'rpm'
        # Actually rpm is in NOISE_STD. I excluded it above. 
        # But wait! We DO want rpm residuals (for misfire).
        # Let's handle rpm explicitly since it uses commanded_rpm for expected, but actual is rpm.
        if "rpm" in row and "rpm" in NOISE_STD:
            actual_rpm = row["rpm"]
            expected_rpm = baseline["rpm"]
            res_rpm = actual_rpm - expected_rpm
            z_rpm = res_rpm / NOISE_STD["rpm"]
            record["rpm_residual"] = res_rpm
            record["rpm_z"] = z_rpm

        residual_records.append(record)
        
    res_df = pd.DataFrame(residual_records)
    res_df.to_csv(out_path, index=False)

def main():
    csv_files = glob.glob(os.path.join(DATASET_DIR, "mission_*.csv"))
    if not csv_files:
        print(f"No mission files found in {DATASET_DIR}")
        return
        
    print(f"Generating residuals for {len(csv_files)} missions...")
    
    for i, csv_path in enumerate(csv_files):
        process_mission(csv_path)
        if (i + 1) % 20 == 0:
            print(f"  Processed {i + 1}/{len(csv_files)}...")
            
    print("Done!")

if __name__ == "__main__":
    main()
