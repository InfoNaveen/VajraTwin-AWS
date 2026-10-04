import argparse
import time
import json
import os
import pandas as pd
import requests

def main():
    parser = argparse.ArgumentParser(description="UAV Live Telemetry Streamer")
    parser.add_argument("--url", default="http://127.0.0.1:8000/twin_analyze", help="Target API URL")
    args = parser.parse_args()

    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'synthetic_telemetry.csv')
    fault_status_path = os.path.join(os.path.dirname(__file__), 'fault_status.json')
    
    # Preload telemetry data
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        print(f"Error: Could not find telemetry data at {data_path}")
        return

    print("=== INITIATING UAV FLIGHT TELEMETRY STREAM ===")
    print(f"Targeting Endpoint: {args.url}")
    print("Streaming at 1 Hz. Press Ctrl+C to abort.\n")

    row_index = 0
    total_rows = len(df)

    def safe_float(val, default=0.0):
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    while True:
        if row_index >= total_rows:
            row_index = 0 # Loop endlessly

        raw_row = df.iloc[row_index]
        
        # 1. Load Live Fault Status dynamically on every single tick
        active_fault = "NONE"
        severity = 0.0
        
        if os.path.exists(fault_status_path):
            try:
                with open(fault_status_path, 'r') as f:
                    fault_data = json.load(f)
                    
                # Support the schema: {"active_fault": "...", "severity": 1.0}
                if "active_fault" in fault_data:
                    active_fault = str(fault_data.get("active_fault", "NONE")).upper()
                    severity = safe_float(fault_data.get("severity", 0.0))
                else:
                    # Fallback if using the old schema
                    if safe_float(fault_data.get("COOLING_FAIL")) > 0:
                        active_fault = "COOLING_FAIL"
                        severity = safe_float(fault_data.get("COOLING_FAIL"))
                    elif safe_float(fault_data.get("OIL_LEAK")) > 0:
                        active_fault = "OIL_LEAK"
                        severity = safe_float(fault_data.get("OIL_LEAK"))
                    elif safe_float(fault_data.get("MISFIRE")) > 0:
                        active_fault = "MISFIRE"
                        severity = safe_float(fault_data.get("MISFIRE"))
            except (json.JSONDecodeError, ValueError):
                pass
                
        cooling_s = severity if active_fault == "COOLING_FAIL" else 0.0
        oil_s = severity if active_fault == "OIL_LEAK" else 0.0
        misfire_s = severity if active_fault == "MISFIRE" else 0.0
        
        print(f"[INJECTOR] Active Scalars -> OIL: {oil_s:.1f}, COOLING: {cooling_s:.1f}, MISFIRE: {misfire_s:.1f}")

        # 2. Mutate Row based on Severity (S)
        mutated_row = raw_row.copy()
        mutated_row["cht_avg_c"] += (50.0 * cooling_s)
        mutated_row["oil_pressure_psi"] -= (15.0 * oil_s)
        mutated_row["vibration_rms_g"] += (3.0 * misfire_s)
        
        fault_str = f"FAULT ACTIVE: {active_fault} (Sev: {severity})" if active_fault != "NONE" else "HEALTHY"

        # 3. Transmit Frame
        payload = {
            "rpm": mutated_row["rpm"],
            "map_kpa": mutated_row["map_kpa"],
            "oat_c": mutated_row["oat_c"],
            "egt_avg_c": mutated_row["egt_avg_c"],
            "cht_avg_c": mutated_row["cht_avg_c"],
            "oil_temp_c": mutated_row["oil_temp_c"],
            "oil_pressure_psi": mutated_row["oil_pressure_psi"],
            "vibration_rms_g": mutated_row["vibration_rms_g"]
        }

        try:
            response = requests.post(args.url, json=payload, timeout=2.0)
            
            if response.status_code == 200:
                data = response.json()
                api_status = data.get("status", "UNKNOWN")
                
                if api_status == "CALIBRATING":
                    print(f"[Tick {row_index:05d}] [BUFFER WARMUP] Status: CALIBRATING")
                elif api_status == "ACTIVE":
                    fault_class = data.get("fault_class", "UNKNOWN")
                    rul = data.get("estimated_rul_minutes", 0.0)
                    advisory = data.get("mission_advisory", "UNKNOWN")
                    print(f"[Tick {row_index:05d}] [ACTIVE] Fault: {fault_class} | RUL: {rul:.1f} mins | Advisory: {advisory}")
                else:
                    print(f"[Tick {row_index:05d}] Unknown API Status: {api_status}")
            else:
                print(f"[Tick {row_index:05d}] ERROR: API returned status code {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"[Tick {row_index:05d}] WARNING: Connection refused. API down? Retrying next second...")
        except requests.exceptions.Timeout:
            print(f"[Tick {row_index:05d}] WARNING: Request timed out. Retrying next second...")
        except requests.exceptions.RequestException as e:
            print(f"[Tick {row_index:05d}] ERROR: HTTP Request failed: {e}")

        row_index += 1
        time.sleep(1.0)

if __name__ == "__main__":
    main()
