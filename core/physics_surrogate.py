def calculate_residuals(payload: dict) -> dict:
    # Extract independent variables
    # No try/except intentionally; fail fast on missing keys
    rpm = payload["rpm"]
    map_kpa = payload["map_kpa"]
    oat_c = payload["oat_c"]

    # Calculate Expected values based on Physics Baselines
    expected_egt = 400 + (2.0 * map_kpa) + (0.05 * rpm)
    expected_cht = oat_c + (0.3 * expected_egt)
    expected_oil_temp = expected_cht * 0.8
    expected_oil_pressure = (0.015 * rpm) - (0.2 * expected_oil_temp) + 20
    expected_vibration = 0.5 + (rpm / 5000.0) ** 2

    # Calculate Residuals (Actual - Expected)
    delta_egt = payload["egt_avg_c"] - expected_egt
    delta_cht = payload["cht_avg_c"] - expected_cht
    delta_oil_temp = payload["oil_temp_c"] - expected_oil_temp
    delta_oil_pressure = payload["oil_pressure_psi"] - expected_oil_pressure
    delta_vibration = payload["vibration_rms_g"] - expected_vibration

    # Return exactly the 5 specified keys
    return {
        "delta_egt": delta_egt,
        "delta_cht": delta_cht,
        "delta_oil_temp": delta_oil_temp,
        "delta_oil_pressure": delta_oil_pressure,
        "delta_vibration": delta_vibration
    }
