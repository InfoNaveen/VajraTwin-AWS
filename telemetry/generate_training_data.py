import pandas as pd
import numpy as np
import os

def generate_training_data(output_path, num_rows=10000):
    np.random.seed(42)
    
    # Initialize arrays
    rpm = np.zeros(num_rows)
    map_kpa = np.zeros(num_rows)
    oat_c = np.zeros(num_rows)
    
    # Initial state
    rpm[0] = 2000
    map_kpa[0] = 50
    oat_c[0] = 25
    
    # Generate independent variables using a smooth random walk
    for i in range(1, num_rows):
        # Calculate random deltas
        delta_rpm = np.random.uniform(-100, 100)
        delta_map = np.random.uniform(-2, 2)
        delta_oat = np.random.uniform(-0.1, 0.1)
        
        # Apply deltas and clip to absolute boundaries
        rpm[i] = np.clip(rpm[i-1] + delta_rpm, 1500, 5800)
        map_kpa[i] = np.clip(map_kpa[i-1] + delta_map, 40, 115)
        oat_c[i] = np.clip(oat_c[i-1] + delta_oat, -10, 45)
        
    # Physics Baselines (Healthy State):
    egt_base = 400 + (2.0 * map_kpa) + (0.05 * rpm)
    cht_base = oat_c + (0.3 * egt_base)
    oil_temp_base = cht_base * 0.8
    oil_pressure_base = (0.015 * rpm) - (0.2 * oil_temp_base) + 20
    vibration_base = 0.5 + (rpm / 5000)**2
    
    # Add minimal Gaussian noise to dependent variables to simulate sensor jitter
    noise_scale = 0.5
    egt_avg_c = egt_base + np.random.normal(0, noise_scale, num_rows)
    cht_avg_c = cht_base + np.random.normal(0, noise_scale, num_rows)
    oil_temp_c = oil_temp_base + np.random.normal(0, noise_scale, num_rows)
    oil_pressure_psi = oil_pressure_base + np.random.normal(0, noise_scale, num_rows)
    vibration_rms_g = vibration_base + np.random.normal(0, 0.05, num_rows)

    df = pd.DataFrame({
        'rpm': rpm,
        'map_kpa': map_kpa,
        'oat_c': oat_c,
        'egt_avg_c': egt_avg_c,
        'cht_avg_c': cht_avg_c,
        'oil_temp_c': oil_temp_c,
        'oil_pressure_psi': oil_pressure_psi,
        'vibration_rms_g': vibration_rms_g
    })
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated {num_rows} rows of time-series training data at {output_path}")

if __name__ == "__main__":
    output_csv = os.path.join(os.path.dirname(__file__), '..', 'data', 'synthetic_telemetry.csv')
    generate_training_data(output_csv)
