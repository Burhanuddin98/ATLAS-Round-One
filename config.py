"""Default simulation configuration for ATLAS_Round_One."""

class SimConfig:
    def __init__(self):
        self.rays = 10000
        self.bounces = 50
        self.time_budget = 2.0  # seconds
        self.seed = 42
