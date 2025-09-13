# project.py — manage state of the current ATLAS session
import geometry
import viz

class ProjectState:
    def __init__(self):
        self.mesh = None
        self.parts = []          # list of (name, trimesh.Trimesh)
        self.matlib = None       # MaterialDB
        self.assignments = {}    # part_name -> material_name
        self.current_part_index = -1

    def set_parts(self, mesh, comps):
        """Update project state with a new mesh + components."""
        self.mesh = mesh
        self.parts = [(f"Part_{i}", c) for i, c in enumerate(comps)]
        self.assignments.clear()

    def material_color_map(self):
        cmap = {}
        for part_name, mat_name in self.assignments.items():
            cmap[part_name] = viz.material_color(mat_name, alpha=0.95)
        return cmap
