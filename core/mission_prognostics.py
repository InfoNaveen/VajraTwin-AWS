import numpy as np

class PrognosticEngine:
    def __init__(self):
        self.current_health = 100.0
        
    def calculate_rul(self, stress_coefficient: float, delta_t_seconds: float = 1.0) -> dict:
        # State Update: Subtract the real-time degradation
        base_drop_per_min = 0.01 * (stress_coefficient ** 3)
        actual_drop = base_drop_per_min * (delta_t_seconds / 60.0)
        
        self.current_health = max(0.0, self.current_health - actual_drop)
        
        # Horizon Edge Case
        if stress_coefficient < 1.5:
            return {
                "current_health": float(self.current_health),
                "estimated_rul_minutes": 999.0,
                "confidence_interval": [999.0, 999.0],
                "mission_advisory": "GO_FLIGHT"
            }
            
        # Vectorized Monte Carlo: Run exactly 100 simulation paths
        mu = base_drop_per_min
        sigma = 0.1 * mu
        
        paths = np.full(100, self.current_health)
        steps = np.zeros(100)
        active = paths > 0
        
        step_count = 0
        while np.any(active) and step_count < 10000:
            step_count += 1
            # Vectorized noise across all 100 paths
            noise = np.random.normal(mu, sigma, size=100)
            # Clip to ensure minimal positive drop to avoid infinite loops if noise < 0
            paths[active] -= np.clip(noise[active], 0.00001, None)
            
            # Find paths that just hit 0 this exact step
            died_this_step = (paths <= 0) & active
            steps[died_this_step] = step_count
            
            # Update active mask for next loop
            active = paths > 0
            
        # Cap any stragglers that didn't die
        steps[active] = 10000
        
        # Extract percentiles
        p5 = np.percentile(steps, 5)
        p95 = np.percentile(steps, 95)
        mean_rul = np.mean(steps)
        
        # Advisory Logic
        if p5 > 60:
            advisory = "GO_FLIGHT"
        elif p5 >= 30:
            advisory = "MAINTENANCE_REQUIRED_POST_FLIGHT"
        elif p5 >= 15:
            advisory = "ABORT_SOON"
        else:
            advisory = "ABORT_IMMEDIATE"
            
        return {
            "current_health": float(self.current_health),
            "estimated_rul_minutes": float(mean_rul),
            "confidence_interval": [float(p5), float(p95)],
            "mission_advisory": advisory
        }
