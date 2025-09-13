# geometry.py
import numpy as np

try:
    import trimesh
except Exception:
    trimesh = None


def _ensure_trimesh():
    if trimesh is None:
        raise RuntimeError("trimesh is not installed in this environment.")


def load_mesh(path: str):
    """Load a mesh/scene and return a single processed Trimesh."""
    _ensure_trimesh()
    m = trimesh.load(path, force="mesh")
    if isinstance(m, trimesh.Scene):
        # Concatenate all geometries in scene
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    # Process (remove degenerate/duplicate faces, fix normals)
    m = m.process(validate=True)
    if m.vertices is None or m.faces is None or len(m.vertices) == 0 or len(m.faces) == 0:
        raise RuntimeError("Loaded mesh is empty or invalid.")
    return m


def split_mesh(m):
    """Split Trimesh into connected components; returns a list[Trimesh]."""
    _ensure_trimesh()
    comps = list(m.split(only_watertight=False))
    # Ensure each comp is processed
    clean = []
    for c in comps:
        cc = c.process(validate=True)
        if cc.vertices is not None and cc.faces is not None and len(cc.faces) > 0:
            clean.append(cc)
    return clean


def make_sample_cube(edge=1.0):
    """Create a simple cube to test drawing without loading a file."""
    _ensure_trimesh()
    cube = trimesh.creation.box(extents=(edge, edge, edge))
    cube.apply_translation([0, 0, edge * 0.5])  # lift a bit above origin
    return cube

# geometry.py (additions)

import numpy as np
try:
    import trimesh
except Exception:
    trimesh = None


def is_watertight(m) -> bool:
    """Robust check for watertightness."""
    if m is None:
        return False
    try:
        return bool(m.is_watertight)
    except Exception:
        return False


def make_bounding_box(m: "trimesh.Trimesh", mode: str = "aabb", pad_rel: float = 0.05):
    """
    Create a thin shell box that encloses mesh m.
    mode: "aabb" (axis-aligned) or "obb" (oriented by principal axes)
    pad_rel: padding as a fraction of the model's max extent
    """
    if trimesh is None:
        raise RuntimeError("trimesh not installed")

    if m.vertices.size == 0:
        raise ValueError("Empty mesh")

    bb_min, bb_max = m.bounds
    diag = float(np.linalg.norm(bb_max - bb_min))
    diag = max(diag, 1e-6)
    pad = diag * float(pad_rel)

    if mode.lower() == "obb":
        # Transform mesh to its principal inertia frame, build AABB there, then transform back.
        T = m.principal_inertia_transform
        m_local = m.copy()
        m_local.apply_transform(np.linalg.inv(T))
        bb_min_l, bb_max_l = m_local.bounds
        extents = (bb_max_l - bb_min_l) + 2 * pad
        center_l = (bb_min_l + bb_max_l) * 0.5
        box_local = trimesh.creation.box(extents=extents)
        box_local.apply_translation(center_l)
        box_local.apply_transform(T)
        box = box_local
    else:
        # AABB with padding
        center = (bb_min + bb_max) * 0.5
        extents = (bb_max - bb_min) + 2 * pad
        box = trimesh.creation.box(extents=extents)
        box.apply_translation(center)

    # Make it inward-facing so interior is "inside the room"
    box.faces = box.faces[:, ::-1]
    return box


def add_enclosure_if_needed(m: "trimesh.Trimesh",
                            parts: list,
                            enabled: bool = True,
                            mode: str = "aabb",
                            pad_rel: float = 0.05,
                            part_name: str = "Bounds"):
    """
    If mesh isn't watertight and 'enabled', append a bounding box part.
    Returns updated parts list.
    """
    if not enabled:
        return parts
    try:
        if not is_watertight(m):
            box = make_bounding_box(m, mode=mode, pad_rel=pad_rel)
            parts = parts + [(part_name, box)]
    except Exception as e:
        print(f"[WARN] add_enclosure_if_needed failed: {e}")
    return parts