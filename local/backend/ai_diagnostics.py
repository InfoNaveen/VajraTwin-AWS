import os
import collections
import joblib
import numpy as np

# Global model loading to prevent cold starts on every request
# Models live alongside this file in local/backend/models/saved/
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'saved')

try:
    iso_forest = joblib.load(os.path.join(MODELS_DIR, 'iso_forest.pkl'))
    rf_classifier = joblib.load(os.path.join(MODELS_DIR, 'rf_classifier.pkl'))
    gb_regressor = joblib.load(os.path.join(MODELS_DIR, 'gb_regressor.pkl'))
except FileNotFoundError as e:
    print(f"Warning: Pre-trained models not found in {MODELS_DIR}. Ensure Phase 3 notebook was run. {e}")
    iso_forest = None
    rf_classifier = None
    gb_regressor = None

class DiagnosticEngine:
    def __init__(self):
        # Stateful rolling buffer
        self.buffer = collections.deque(maxlen=5)
        self.keys = [
            'delta_egt', 
            'delta_cht', 
            'delta_oil_temp', 
            'delta_oil_pressure', 
            'delta_vibration'
        ]

    def process_frame(self, residuals: dict) -> dict:
        self.buffer.append(residuals)

        # Warm-up Logic
        if len(self.buffer) < 5:
            return {
                "anomaly_score": 0.0,
                "fault_class": "UNKNOWN",
                "stress_coefficient": 1.0,
                "status": "CALIBRATING"
            }

        # Feature Engineering without Pandas for ultra-low latency
        means = []
        diffs = []
        for key in self.keys:
            vals = [frame[key] for frame in self.buffer]
            means.append(sum(vals) / 5.0)
            diffs.append(vals[4] - vals[3])
            
        features = means + diffs
        X = np.array([features])

        # Inference
        anomaly_pred = iso_forest.predict(X)[0] # -1 is anomaly, 1 is normal
        anomaly_score = 1.0 if anomaly_pred == -1 else 0.0
        
        fault_class = rf_classifier.predict(X)[0]
        stress_coefficient = gb_regressor.predict(X)[0]

        return {
            "anomaly_score": float(anomaly_score),
            "fault_class": str(fault_class),
            "stress_coefficient": float(stress_coefficient),
            "status": "ACTIVE"
        }
