# materials_tools.py
import inspect
import numpy as np

def ensure_free_space_material(matlib, refresh_fn, logger, name_candidates=("Free Space", "FreeSpace", "Boundary", "Absorbing Boundary")):
    """
    Ensure a 'Free Space' (or equivalent) material exists in matlib.
    If missing, create a synthetic one compatible with your Material class signature.
    Returns the chosen/created name, or None on failure.
    """
    if not matlib:
        return None

    # existing?
    for cand in name_candidates:
        if cand in matlib.items:
            return cand

    # create synthetic
    try:
        from materials import Material
        freqs = getattr(matlib, "native_bands", None) or [125, 250, 500, 1000, 2000, 4000]
        n = len(freqs)
        alpha = [1.0] * n
        scatter = [0.0] * n
        tau = [0.0] * n

        sig = inspect.signature(Material.__init__)
        params = sig.parameters

        kwargs = {}
        if "name" in params:    kwargs["name"] = "Free Space"
        if "alpha" in params:   kwargs["alpha"] = alpha
        if "scatter" in params: kwargs["scatter"] = scatter
        if "freqs" in params:   kwargs["freqs"] = freqs
        if "tau" in params:     kwargs["tau"] = tau
        if "bands" in params and "bands" not in kwargs:
            kwargs["bands"] = freqs
        if "absorption" in params and "absorption" not in kwargs:
            kwargs["absorption"] = alpha

        mat = Material(**kwargs)
        # normalize arrays if needed
        for attr, val in (("alpha", alpha), ("scatter", scatter), ("freqs", freqs), ("tau", tau)):
            try:
                if hasattr(mat, attr) and not isinstance(getattr(mat, attr), np.ndarray):
                    setattr(mat, attr, np.asarray(val, dtype=float))
            except Exception:
                pass

        matlib.items["Free Space"] = mat
        try:
            refresh_fn()
        except Exception:
            pass
        logger.log('Created synthetic material "Free Space" (α=1 across bands).')
        return "Free Space"
    except Exception as e:
        logger.log(f"Failed to create synthetic 'Free Space': {e}", error=True)
        return None
