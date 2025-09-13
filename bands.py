"""Band utilities (resample, ISO centers)."""

import numpy as np

def resample_bands(src_freqs, src_vals, dst_freqs):
    """Log-frequency interpolation from src to dst."""
    return np.interp(np.log10(dst_freqs), np.log10(src_freqs), src_vals)
