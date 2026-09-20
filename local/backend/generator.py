import csv
import json
import time
import os
import requests
from datetime import datetime

TARGET_URL = "http://localhost:8000/twin_analyze"

def load_fault_status(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception:
        return {"active_fault": "NONE", "severity": 0.0}

def apply_fault(row, fault_status):
    fault = fault_status.get("active_fault", "NONE")
    severity = fault_status.get("severity", 0.0)
    
    if fault == "NONE" or severity == 0.0:
        return row
        
    mutated_row = row.copy()
    
    if fault == "OIL_LEAK":
        mutated_row['oil_pressure_psi'] = row['oil_pressure_psi'] * (1 - 0.6 * severity)
        mutated_row['oil_temp_c'] = row['oil_temp_c'] + (20 * severity)
        mutated_row['vibration_rms_g'] = row['vibration_rms_g'] * (1 + 0.5 * severity)
        
    elif fault == "COOLING_FAIL":
        mutated_row['cht_avg_c'] = row['cht_avg_c'] + (45 * severity)
        mutated_row['oil_temp_c'] = row['oil_temp_c'] + (30 * severity)
        mutated_row['oil_pressure_psi'] = row['oil_pressure_psi'] * (1 - 0.3 * severity)
        
    elif fault == "MISFIRE":
        mutated_row['egt_avg_c'] = row['egt_avg_c'] * (1 - 0.3 * severity)
        mutated_row['vibration_rms_g'] = row['vibration_rms_g'] * (1 + 4.0 * severity)
        mutated_row['cht_avg_c'] = row['cht_avg_c'] - (15 * severity)
        
    return mutated_row

def stream_telemetry(csv_filepath, fault_filepath):
    while True:
        try:
            with open(csv_filepath, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    start_time = time.time()
                    
                    # Convert string values to float
                    for k in row:
                        row[k] = float(row[k])
                        
                    # Read fault status
                    fault_status = load_fault_status(fault_filepath)
                    
                    # Apply fault mutations
                    mutated_row = apply_fault(row, fault_status)
                    
                    # Package payload
                    payload = mutated_row.copy()
                    payload['timestamp'] = datetime.utcnow().isoformat() + "Z"
                    
                    # Send HTTP POST request
                    try:
                        requests.post(TARGET_URL, json=payload, timeout=0.5)
                    except requests.exceptions.RequestException:
                        pass  # Prevent crashing if server is down
                    
                    # Enforce strict 1-second interval execution (clock drift compensation)
                    elapsed = time.time() - start_time
                    sleep_time = max(0.0, 1.0 - elapsed)
                    time.sleep(sleep_time)
                    
        except FileNotFoundError:
            print(f"Error: {csv_filepath} not found. Please run generate_training_data.py first.")
            time.sleep(5)

if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    csv_file = os.path.join(base_dir, '..', 'data', 'synthetic_telemetry.csv')
    fault_file = os.path.join(base_dir, 'fault_status.json')
    
    print("Starting telemetry streamer...")
    stream_telemetry(csv_file, fault_file)
