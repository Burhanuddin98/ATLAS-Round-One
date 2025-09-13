from PySide6 import QtWidgets, QtCore, QtGui
import sys, os, json, traceback

import geometry, viz
from material_db import MaterialDB
from logger import Logger
from project import ProjectState
from ui_helpers import make_geometry_dock, make_materials_dock, make_log_dock

DEFAULT_LIB = os.path.join(os.path.dirname(__file__), "material_library_1_3oct.json")


def log_exc(prefix: str) -> str:
    return f"{prefix}:\n{traceback.format_exc()}"


class MainWindow(QtWidgets.QMainWindow):


    def _ensure_free_space_material(
        self,
        name_candidates=("Free Space", "FreeSpace", "Boundary", "Absorbing Boundary")
    ):
        """
        Ensure a 'free space' material exists in the library.
        If not, create a synthetic one with α=1 across bands and minimal scatter.
        Works with different Material __init__ signatures (alpha/scatter/freqs/tau...).
        Returns the chosen/created material name, or None on failure.
        """
        if not self.state.matlib:
            return None

        # 1) Use an existing candidate if present
        for cand in name_candidates:
            if cand in self.state.matlib.items:
                return cand

        # 2) Create synthetic, adapting to your Material signature
        try:
            import inspect
            import numpy as np
            from materials import Material  # your class

            freqs = getattr(self.state.matlib, "native_bands", None)
            if freqs is None:
                # fallback: standard octave centers
                freqs = [125, 250, 500, 1000, 2000, 4000]
            n = len(freqs)
            alpha = [1.0] * n           # fully absorbing
            scatter = [0.0] * n         # no scattering
            tau = [0.0] * n             # default time/lag if required

            # Build kwargs only for parameters the constructor actually accepts
            sig = inspect.signature(Material.__init__)
            params = sig.parameters

            kwargs = {}
            if "name" in params:    kwargs["name"] = "Free Space"
            if "alpha" in params:   kwargs["alpha"] = alpha
            if "scatter" in params: kwargs["scatter"] = scatter
            if "freqs" in params:   kwargs["freqs"] = freqs
            if "tau" in params:     kwargs["tau"] = tau
            # common alternates some repos use
            if "bands" in params and "bands" not in kwargs:
                kwargs["bands"] = freqs
            if "absorption" in params and "absorption" not in kwargs:
                kwargs["absorption"] = alpha

            # Create the material
            mat = Material(**kwargs)

            # Some implementations expect numpy arrays
            # Try to set attributes if present (best-effort, harmless if missing)
            for attr, val in (("alpha", alpha), ("scatter", scatter), ("freqs", freqs), ("tau", tau)):
                try:
                    if hasattr(mat, attr) and not isinstance(getattr(mat, attr), np.ndarray):
                        setattr(mat, attr, np.asarray(val, dtype=float))
                except Exception:
                    pass

            # Register in the DB and refresh UI
            self.state.matlib.items["Free Space"] = mat
            self.refresh_materials_list()
            self.logger.log('Created synthetic material "Free Space" (α=1 across bands).')
            return "Free Space"

        except Exception as e:
            self.logger.log(f"Failed to create synthetic 'Free Space': {e}", error=True)
            return None



    def _enclosure_settings(self):
        enabled = bool(self.chk_enclosure.isChecked())
        mode_text = self.combo_enclosure_mode.currentText().lower()
        mode = "aabb" if "aabb" in mode_text else "obb"
        pad = float(self.spin_pad.value()) / 100.0  # percent -> relative
        return enabled, mode, pad


    def _add_or_update_enclosure(self, force=False):
        """
        Ensure a 'Bounds' part exists with current enclosure settings.
        If force=True, add/update regardless of watertightness.
        Auto-assign Free Space to Bounds.
        """
        if not self.state.mesh:
            self.logger.log("Load a mesh before adding enclosure.", error=True)
            return

        enabled, mode, pad = self._enclosure_settings()
        if not enabled and not force:
            self.logger.log("Enclosure disabled; enable the checkbox or press the button to force-add.", error=True)
            return

        # Remove existing Bounds if present (update behavior)
        parts_wo_bounds = [(n, c) for (n, c) in self.state.parts if n != "Bounds"]

        # Call geometry helper (force means: pretend not watertight by passing enabled=True always)
        try:
            named = geometry.add_enclosure_if_needed(
                self.state.mesh,
                parts_wo_bounds,
                enabled=True,       # always true here, because we're forcing
                mode=mode,
                pad_rel=pad,
                part_name="Bounds",
            )
            self.state.parts = named
            self.refresh_parts_list()
            self._draw()
            # Ensure Free Space exists and assign
            free_name = self._ensure_free_space_material()
            if free_name:
                self.state.assignments["Bounds"] = free_name
                self.logger.log(f'Assigned "{free_name}" → Bounds')
                self.refresh_parts_list()
                self._draw(highlight_name="Bounds")
        except Exception:
            err = log_exc("Add/Update enclosure failed")
            self.logger.log(err, error=True)
            QtWidgets.QMessageBox.critical(self, "Enclosure Failed", err)

    def on_enclosure_now(self):
        self._add_or_update_enclosure(force=True)


    def __init__(self):
        super().__init__()
        self.setWindowTitle("ATLAS Round One")
        self.resize(1640, 940)

        # ---------- State ----------
        self.state = ProjectState()
        self.logger = None
        self.current_project_file = None    # path to .atlasproj.json
        self.current_mesh_path = None       # path to mesh on disk

        # ---------- Central Viewer ----------
        self.canvas, self.view = viz.init_canvas()
        self.setCentralWidget(self.canvas.native)

        # ---------- Docks ----------
        # NOTE: ui_helpers now returns enclosure widgets too
        (
            self.dock_geo,
            self.combo_mode,
            self.parts_list,
            
            self.chk_enclosure,
            self.combo_enclosure_mode,
            self.spin_pad,
            self.btn_enclosure_now
        ) = make_geometry_dock(
            self, self.on_load_geometry, self.on_mode_changed, self.on_part_selected, self.on_enclosure_now
        )


        self.dock_mat, self.search_mat, self.materials_list, self.plot = make_materials_dock(
            self, self.refresh_materials_list, self.on_material_selected, self.on_assign_material
        )
        self.dock_log, self.log_box = make_log_dock(self)
        self.logger = Logger(self.log_box, self.statusBar())

        # ---------- Menu ----------
        self._build_menu()

        # ---------- Autoload materials ----------
        if os.path.exists(DEFAULT_LIB):
            try:
                self.state.matlib = MaterialDB.from_json(DEFAULT_LIB)
                self.logger.log(
                    f"Materials auto-loaded: {len(self.state.matlib.items)} entries from {os.path.basename(DEFAULT_LIB)}"
                )
                self.refresh_materials_list()
            except Exception:
                self.logger.log(log_exc("Material auto-load failed"), error=True)

        self.logger.log("Ready.")

    # =================== Menu ===================
    def _build_menu(self):
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")

        act_new = QtGui.QAction("New Project", self)
        act_new.triggered.connect(self.new_project)

        act_open = QtGui.QAction("Open Project…", self)
        act_open.triggered.connect(self.open_project)

        act_save = QtGui.QAction("Save Project", self)
        act_save.triggered.connect(self.save_project)

        act_save_as = QtGui.QAction("Save Project As…", self)
        act_save_as.triggered.connect(self.save_project_as)

        act_exit = QtGui.QAction("Exit", self)
        act_exit.triggered.connect(self.close)

        for a in (act_new, act_open, act_save, act_save_as, act_exit):
            file_menu.addAction(a)


    # =================== Logging/Drawing ===================
    def _draw(self, highlight_name=None):
        if not self.state.parts:
            return
        viz.draw_parts(
            self.view,
            self.state.parts,
            mode=("wireframe" if self.combo_mode.currentText().lower().startswith("wire") else "shaded"),
            color_map=self.state.material_color_map(),
            highlight_name=highlight_name,
        )
        self.canvas.update()

    def refresh_parts_list(self):
        self.parts_list.clear()
        # put Bounds last
        parts = [p for p in self.state.parts if p[0] != "Bounds"] + \
                [p for p in self.state.parts if p[0] == "Bounds"]
        for name, comp in parts:
            mat = self.state.assignments.get(name, "(none)")
            self.parts_list.addItem(f"{name} | faces={len(comp.faces)} | area={comp.area:.3f} | mat={mat}")

    def _parts_context_menu(self, pos):
        item = self.parts_list.itemAt(pos)
        if not item:
            return
        name = item.text().split("|", 1)[0].strip()  # extract part name
        menu = QtWidgets.QMenu(self)
        act_assign_fs = menu.addAction('Assign "Free Space" to Bounds')
        action = menu.exec_(self.parts_list.mapToGlobal(pos))
        if action == act_assign_fs:
            free_name = self._ensure_free_space_material()
            if not free_name:
                return
            # If user clicked any line but we only want to assign Bounds, enforce name
            target = "Bounds"
            # ensure Bounds exists; if not, try to add it
            if not any(n == "Bounds" for n, _ in self.state.parts):
                self._add_or_update_enclosure(force=True)
            self.state.assignments[target] = free_name
            self.logger.log(f'Assigned "{free_name}" → {target}')
            self.refresh_parts_list()
            self._draw(highlight_name=target)


    # =================== Geometry actions ===================
    def on_load_geometry(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select 3D model", os.getcwd(), "Mesh (*.obj *.stl *.ply *.glb *.gltf)"
        )
        if not path:
            self.logger.log("No file selected.")
            return
        self._load_mesh_from_path(path)

    def _load_mesh_from_path(self, path: str):
        """Load mesh, split, add enclosure if requested, recolor + refresh UI."""
        self.logger.log(f"Loading mesh: {path}")
        try:
            m = geometry.load_mesh(path)
            comps = geometry.split_mesh(m)

            # enclosure settings from UI
            enabled, mode, pad = self._enclosure_settings()
            named = [(f"Part_{i}", c) for i, c in enumerate(comps)]
            named = geometry.add_enclosure_if_needed(
                m,
                named,
                enabled=enabled,
                mode=mode,
                pad_rel=pad,
                part_name="Bounds",
            )

            # set state
            self.state.parts = named
            self.state.mesh = m
            self.state.assignments.clear()
            self.current_mesh_path = path

            # Auto-assign "Free Space" to Bounds if present
            if any(n == "Bounds" for n, _ in self.state.parts):
                free_name = self._ensure_free_space_material()
                if free_name:
                    self.state.assignments["Bounds"] = free_name
                    self.logger.log(f'Auto-assigned "{free_name}" to Bounds')


            self.refresh_parts_list()
            self._draw()
            self.logger.log(f"Loaded {len(self.state.parts)} parts from {os.path.basename(path)}")
        except Exception:
            err = log_exc("Geometry load failed")
            self.logger.log(err, error=True)
            QtWidgets.QMessageBox.critical(self, "Geometry load failed", err)

    def on_part_selected(self, row: int):
        self.state.current_part_index = row
        if 0 <= row < len(self.state.parts):
            self._draw(highlight_name=self.state.parts[row][0])

    def on_mode_changed(self, idx: int):
        if self.state.parts:
            self.logger.log(f"Render mode: {self.combo_mode.currentText()}")
            part_name = (
                self.state.parts[self.state.current_part_index][0]
                if 0 <= self.state.current_part_index < len(self.state.parts)
                else None
            )
            self._draw(highlight_name=part_name)

    # =================== Materials actions ===================
    def refresh_materials_list(self):
        self.materials_list.clear()
        if not self.state.matlib:
            self.materials_list.addItem("(no materials)")
            return
        q = self.search_mat.text().strip().lower()
        for n in sorted(self.state.matlib.items.keys()):
            if q and q not in n.lower():
                continue
            self.materials_list.addItem(n)

    def on_material_selected(self, row: int):
        if not self.state.matlib or row < 0:
            return
        item = self.materials_list.item(row)
        if not item:
            return
        mat = self.state.matlib.items.get(item.text())
        if not mat:
            return
        self.plot.plot_absorption(self.state.matlib.native_bands, mat.alpha, mat.scatter, title=item.text())

    def on_assign_material(self):
        idx = self.state.current_part_index
        mat_item = self.materials_list.currentItem()
        if idx < 0 or idx >= len(self.state.parts) or not mat_item:
            self.logger.log("Select a part and a material first.", error=True)
            return
        part_name = self.state.parts[idx][0]
        mat_name = mat_item.text()
        self.state.assignments[part_name] = mat_name
        self.logger.log(f"Assigned {mat_name} → {part_name}")
        self.refresh_parts_list()
        self._draw(highlight_name=part_name)

    # =================== Project (Save/Load) ===================
    def _enclosure_settings(self):
        """Read enclosure UI -> (enabled:bool, mode:str, pad:float)."""
        enabled = bool(self.chk_enclosure.isChecked())
        mode_text = self.combo_enclosure_mode.currentText().lower()
        mode = "aabb" if "aabb" in mode_text else "obb"
        pad = float(self.spin_pad.value()) / 100.0  # percent -> relative
        return enabled, mode, pad

    def _current_render_mode(self):
        return "wireframe" if self.combo_mode.currentText().lower().startswith("wire") else "shaded"

    def _serialize_project(self) -> dict:
        enabled, mode, pad = self._enclosure_settings()
        data = {
            "version": 1,
            "mesh_path": self.current_mesh_path,
            "render_mode": self._current_render_mode(),
            "assignments": self.state.assignments,  # {part_name: material_name}
            "enclosure": {"enabled": enabled, "mode": mode, "pad": pad},
        }
        return data

    def _load_project_dict(self, data: dict):
        # Enclosure UI
        enc = data.get("enclosure", {})
        enc_enabled = bool(enc.get("enabled", True))
        enc_mode = enc.get("mode", "aabb")
        enc_pad = float(enc.get("pad", 0.05))

        self.chk_enclosure.setChecked(enc_enabled)
        self.combo_enclosure_mode.setCurrentText("AABB (fast)" if enc_mode == "aabb" else "OBB (tight)")
        self.spin_pad.setValue(int(round(enc_pad * 100.0)))

        # Render mode UI
        rm = data.get("render_mode", "shaded").lower()
        self.combo_mode.setCurrentText("Wireframe" if rm.startswith("wire") else "Shaded")

        # Mesh + parts
        mesh_path = data.get("mesh_path")
        if mesh_path and os.path.exists(mesh_path):
            self._load_mesh_from_path(mesh_path)
        else:
            self.logger.log("Project has no mesh_path or file missing. Load a model manually.", error=True)

        # Assignments (apply only for parts that exist)
        loaded_assignments = data.get("assignments", {})
        applied = 0
        for name, _ in self.state.parts:
            if name in loaded_assignments:
                self.state.assignments[name] = loaded_assignments[name]
                applied += 1
        self.logger.log(f"Restored {applied} material assignments from project.")
        self.refresh_parts_list()
        self._draw()

    def new_project(self):
        self.state = ProjectState()
        self.current_project_file = None
        self.current_mesh_path = None
        # reset UI
        self.parts_list.clear()
        self.search_mat.clear()
        self.combo_mode.setCurrentText("Shaded")
        self.chk_enclosure.setChecked(True)
        self.combo_enclosure_mode.setCurrentText("AABB (fast)")
        self.spin_pad.setValue(5)
        self.view.scene.children[:] = [c for c in self.view.scene.children if not isinstance(c, (viz.visuals.Mesh, viz.visuals.Line))]  # safety
        self.logger.log("New project.")

    def open_project(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open ATLAS Project", os.getcwd(), "ATLAS Project (*.atlasproj.json)"
        )
        if not path:
            return
        try:
            data = json.load(open(path, "r", encoding="utf-8"))
            self.current_project_file = path
            self._load_project_dict(data)
            self.logger.log(f"Opened project: {os.path.basename(path)}")
        except Exception:
            err = log_exc("Open project failed")
            self.logger.log(err, error=True)
            QtWidgets.QMessageBox.critical(self, "Open Project Failed", err)

    def save_project(self):
        if not self.current_project_file:
            return self.save_project_as()
        try:
            data = self._serialize_project()
            json.dump(data, open(self.current_project_file, "w", encoding="utf-8"), indent=2)
            self.logger.log(f"Saved project: {os.path.basename(self.current_project_file)}")
        except Exception:
            err = log_exc("Save project failed")
            self.logger.log(err, error=True)
            QtWidgets.QMessageBox.critical(self, "Save Project Failed", err)

    def save_project_as(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save ATLAS Project As", os.getcwd(), "ATLAS Project (*.atlasproj.json)"
        )
        if not path:
            return
        # ensure extension
        if not path.lower().endswith(".atlasproj.json"):
            path += ".atlasproj.json"
        self.current_project_file = path
        self.save_project()


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
