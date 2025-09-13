# geometry_tools.py
import numpy as np

try:
    import trimesh
except Exception:
    trimesh = None

def is_watertight(m) -> bool:
    if m is None:
        return False
    try:
        return bool(m.is_watertight)
    except Exception:
        return False

def make_bounding_box(m, mode: str = "aabb", pad_rel: float = 0.05):
    if trimesh is None:
        raise RuntimeError("trimesh not installed")
    if m.vertices.size == 0:
        raise ValueError("Empty mesh")
    bb_min, bb_max = m.bounds
    diag = float(np.linalg.norm(bb_max - bb_min))
    diag = max(diag, 1e-6)
    pad = diag * float(pad_rel)

    if mode.lower() == "obb":
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
        center = (bb_min + bb_max) * 0.5
        extents = (bb_max - bb_min) + 2 * pad
        box = trimesh.creation.box(extents=extents)
        box.apply_translation(center)

    # inward normals
    box.faces = box.faces[:, ::-1]
    return box

def add_or_update_enclosure(mesh, parts_named, enabled: bool, mode: str, pad_rel: float,
                            force: bool = False, part_name: str = "Bounds"):
    """
    Returns a new parts list, optionally appending or replacing 'Bounds'.
    If force=True, adds/update regardless of watertightness.
    """
    # strip any existing Bounds
    parts_clean = [(n, c) for (n, c) in parts_named if n != part_name]
    if not enabled and not force:
        return parts_clean
    try:
        if force or not is_watertight(mesh):
            box = make_bounding_box(mesh, mode=mode, pad_rel=pad_rel)
            return parts_clean + [(part_name, box)]
        else:
            return parts_clean
    except Exception as e:
        print(f"[WARN] add_or_update_enclosure failed: {e}")
        return parts_clean

def reorder_bounds_last(parts_named):
    return [p for p in parts_named if p[0] != "Bounds"] + [p for p in parts_named if p[0] == "Bounds"]
