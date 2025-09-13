# project_io.py

def serialize_project(*, mesh_path, assignments, render_mode, enclosure, version=1):
    """
    Returns a dict ready to json.dump()
    enclosure = {"enabled": bool, "mode": "aabb"/"obb", "pad": float_rel}
    """
    return {
        "version": int(version),
        "mesh_path": mesh_path,
        "render_mode": render_mode,
        "assignments": assignments,
        "enclosure": {
            "enabled": bool(enclosure.get("enabled", True)),
            "mode": enclosure.get("mode", "aabb"),
            "pad": float(enclosure.get("pad", 0.05)),
        },
    }

def load_project_into_state(data: dict):
    """
    Prepares UI values and returns (ui_restore_dict, mesh_path).
    Caller is responsible for actually loading the mesh and applying assignments.
    """
    enc = data.get("enclosure", {})
    enc_enabled = bool(enc.get("enabled", True))
    enc_mode = enc.get("mode", "aabb")
    enc_pad = float(enc.get("pad", 0.05))

    ui_restore = {
        "enclosure_enabled": enc_enabled,
        "enclosure_mode_text": "AABB (fast)" if enc_mode == "aabb" else "OBB (tight)",
        "enclosure_pad_percent": int(round(enc_pad * 100.0)),
        "render_mode_text": "Wireframe" if str(data.get("render_mode", "shaded")).lower().startswith("wire") else "Shaded",
    }
    mesh_path = data.get("mesh_path")
    return ui_restore, mesh_path
