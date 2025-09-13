# materials_tools.py
import inspect
import numpy as np

def ensure_free_space_material(matlib, refresh_fn, logger,
                               name_candidates=("Free Space", "FreeSpace", "Boundary", "Absorbing Boundary")):
    """
    Ensure a 'Free Space' (or equivalent) material exists in matlib.
    If missing, create a synthetic one compatible with your Material class signature.
    Returns the chosen/created name, or None on failure.
    """
    if matlib is None:
        return None

    # 1) If exists, just return
    try:
        items = matlib.items  # should be a dict-like
    except Exception:
        logger.log("Material DB missing 'items' mapping.", error=True)
        return None

    for cand in name_candidates:
        try:
            if cand in items:
                return cand
        except Exception:
            # if items isn't a normal dict
            pass

    # 2) Create synthetic (be careful with numpy truthiness)
    try:
        from materials import Material

        # Get bands without boolean evaluation of arrays
        freqs_attr = getattr(matlib, "native_bands", None)
        if freqs_attr is None:
            freqs = [125, 250, 500, 1000, 2000, 4000]
        else:
            freqs = np.asarray(freqs_attr, dtype=float).ravel().tolist()

        n = len(freqs)
        alpha = [1.0] * n     # fully absorbing
        scatter = [0.0] * n   # no scatter
        tau = [0.0] * n       # default if required

        # Build kwargs only for parameters the constructor accepts
        sig = inspect.signature(Material.__init__)
        params = sig.parameters

        kwargs = {}
        if "name" in params:    kwargs["name"] = "Free Space"
        if "alpha" in params:   kwargs["alpha"] = alpha
        if "scatter" in params: kwargs["scatter"] = scatter
        if "freqs" in params:   kwargs["freqs"] = freqs
        if "tau" in params:     kwargs["tau"] = tau
        # common alternates
        if "bands" in params and "bands" not in kwargs:
            kwargs["bands"] = freqs
        if "absorption" in params and "absorption" not in kwargs:
            kwargs["absorption"] = alpha

        mat = Material(**kwargs)

        # Coerce attributes to numpy arrays if needed, without ambiguous truth checks
        for attr, val in (("alpha", alpha), ("scatter", scatter), ("freqs", freqs), ("tau", tau)):
            if hasattr(mat, attr):
                current = getattr(mat, attr)
                if not isinstance(current, np.ndarray):
                    try:
                        setattr(mat, attr, np.asarray(val, dtype=float))
                    except Exception:
                        pass

        items["Free Space"] = mat
        try:
            refresh_fn()
        except Exception:
            pass
        logger.log('Created synthetic material "Free Space" (α=1 across bands).')
        return "Free Space"

    except Exception as e:
        logger.log(f"Failed to create synthetic 'Free Space': {e}", error=True)
        return None
