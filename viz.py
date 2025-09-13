# viz.py — GPU-accelerated VisPy viewer (MSAA, depth, smooth shading) with highlight & wireframe
import numpy as np

try:
    from vispy import scene
    from vispy.scene import visuals
except Exception:
    scene = None
    visuals = None


def init_canvas():
    if scene is None:
        raise RuntimeError("VisPy is not installed. Install it (conda-forge vispy).")

    canvas = scene.SceneCanvas(
        keys=None,
        bgcolor="black",
        size=(960, 720),
        show=False,
        config=dict(samples=4, depth_size=24)  # 4×MSAA + 24-bit depth
    )

    view = canvas.central_widget.add_view()
    view.camera = scene.cameras.TurntableCamera(
        fov=45.0, azimuth=45.0, elevation=25.0, distance=3.0, up='+z'
    )

    # Axis gizmo (small overlay)
    axis = visuals.XYZAxis()
    axis.transform = scene.transforms.STTransform(translate=(50, 50))
    axis_parent = scene.widgets.ViewBox(border_color=None, parent=canvas.scene)
    axis_parent.camera = scene.cameras.PanZoomCamera(aspect=1)
    axis_parent.add(axis)

    return canvas, view


def draw_parts(view, parts, mode="shaded", color_map=None, highlight_name=None):
    """
    Draw list of (part_name, trimesh.Trimesh)
    - mode: "shaded" | "wireframe"
    - color_map: dict part_name -> (r,g,b,a)
    - highlight_name: part to glow (overrides color)
    """
    if scene is None or visuals is None:
        raise RuntimeError("VisPy not available.")

    # clear previous mesh/line visuals
    for obj in list(view.scene.children):
        if isinstance(obj, (visuals.Mesh, visuals.Line)):
            obj.parent = None

    any_drawn = False
    for name, comp in parts:
        V = np.asarray(comp.vertices, dtype=np.float32)
        F = np.asarray(comp.faces, dtype=np.uint32)
        if V.size == 0 or F.size == 0:
            continue

        if not any_drawn:
            _autofit_camera(view, V)

        if mode == "wireframe":
            _draw_wireframe_part(view, V, comp,
                                 (1.0, 1.0, 1.0, 1.0) if name != highlight_name else (1.0, 0.9, 0.2, 1.0))
        else:
            col = (0.8, 0.85, 0.9, 0.95)
            if color_map and name in color_map:
                col = color_map[name]
            if name == highlight_name:
                col = (1.0, 0.85, 0.2, 0.95)  # highlight
            visuals.Mesh(vertices=V, faces=F, color=col,
                         parent=view.scene, shading="smooth")
        any_drawn = True

    view.canvas.update()


def material_color(name: str, alpha=0.95):
    """Deterministic color from material name."""
    h = abs(hash(name)) % (256 * 256 * 256)
    r = ((h >> 16) & 255) / 255.0
    g = ((h >> 8) & 255) / 255.0
    b = (h & 255) / 255.0
    return (r * 0.8 + 0.2, g * 0.8 + 0.2, b * 0.8 + 0.2, alpha)


def _draw_wireframe_part(view, V, comp, color):
    try:
        edges = comp.edges_unique
    except Exception:
        F = comp.faces
        e01 = F[:, [0, 1]]
        e12 = F[:, [1, 2]]
        e20 = F[:, [2, 0]]
        edges = np.unique(np.sort(np.vstack([e01, e12, e20]), axis=1), axis=0)

    visuals.Line(pos=V.astype(np.float32),
                 connect=edges.astype(np.uint32),
                 color=color,
                 width=1.0,
                 parent=view.scene,
                 antialias=True)


def _autofit_camera(view, vertices: np.ndarray):
    if vertices.size == 0:
        return
    bb_min = vertices.min(axis=0)
    bb_max = vertices.max(axis=0)
    center = (bb_min + bb_max) * 0.5
    extent = float(np.linalg.norm(bb_max - bb_min))
    extent = max(extent, 1e-3)
    cam = view.camera
    cam.center = center
    cam.distance = extent * 1.6
