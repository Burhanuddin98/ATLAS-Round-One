
from dataclasses import dataclass
import numpy as np

@dataclass
class Material:
    name: str
    freqs: np.ndarray
    alpha: np.ndarray
    tau: np.ndarray
    scatter: np.ndarray
    kind: str = "generic"
