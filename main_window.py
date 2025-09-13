from PySide6 import QtWidgets, QtGui
import os, json, traceback

import geometry, viz
from material_db import MaterialDB
from logger import Logger
from project import ProjectState
from ui_helpers import make_geometry_dock, make_materials_dock, make_log_dock
from geometry_tools import add_or_update_enclosure, reorder_bounds_last
from materials_tools import ensure_free_space_material
from project_io import serialize_project, load_project_into_state

DEFAULT_LIB = os.path.join(os.path.dirname(__file__), "material_library_1_3oct.json")

def log_exc(prefix: str) -> str:
    return f"{prefix}:\n{traceback.format_exc()}"

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ATLAS Round One")
        self.resize(1640, 940)

        # ---------- State ----------
        self.state = ProjectState()
        self.logger = None
        self.current_project_file = None
        self.current_mesh_path = None

        # ---------- Central Viewer ----------
        self.canvas, self.view = viz.init_canvas()
        self.setCentralWidget(self.canvas.native)

        # ---------- Docks ----------
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

        # Right-click for parts list (Assign Free Space → Bounds)
        self.parts_list.customContextMenuRequested.connect(self._parts_context_menu)

        # ---------- Menu ----------
        self._build_menu()

        # ---------- Autoload materials ----------
        if os.path.exists(DEFAULT_LIB):
            try:
                self.state.matlib = MaterialDB.from_json(DEFAULT_LIB)
                self.logger.log(f"Materials auto-loaded: {len(self.state.matlib.items)} entries")
                self.refresh_materials_list()
            except Exception:
                self.logger.log(log_exc("Material auto-load failed"), error=True)

        self.logger.log("Ready.")

    # =================== Menu ===================
    def _build_menu(self):
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")

        act_new = QtGui.QAction("New Project", self);  act_new.triggered.connect(self.new_project)
        act_open = QtGui.QAction("Open Project…", self); act_open.triggered.connect(self.open_project)
        act_save = QtGui.QAction("Save Project", self); act_save.triggered.connect(self.save_project)
        act_save_as = QtGui.QAction("Save Project As…", self); act_save_as.triggered.connect(self.save_project_as)
        act_exit = QtGui.QAction("Exit", self); act_exit.triggered.connect(self.close)

        for a in (act_new, act_open, act_save, act_save_as, act_exit):
            file_menu.addAction(a)

    # =================== Helpers ===================
    def _enclosure_settings(self):
        enabled = bool(self.chk_enclosure.isChecked())
        mode_text = self.combo_enclosure_mode.currentText().lower()
        mode = "aabb" if "aabb" in mode_text else "obb"
        pad = float(self.spin_pad.value()) / 100.0
        return enabled, mode, pad

    def _current_render_mode(self):
        return "wireframe" if self.combo_mode.currentText().lower().startswith("wire") else "shaded"

    def _draw(self, highlight_name=None):
        if not self.state.parts:
            return
        viz.draw_parts(
            self.view,
            self.state.parts,
            mode=self._current_render_mode(),
            color_map=self.state.material_color_map(),
            highlight_name=highlight_name,
        )
        self.canvas.update()

    def refresh_parts_list(self):
        self.parts_list.clear()
        for name, comp in reorder_bounds_last(self.state.parts):
            mat = self.state.assignments.get(name, "(none)")
            self.parts_list.addItem(f"{name} | faces={len(comp.faces)} | area={comp.area:.3f} | mat={mat}")

    # =================== Geometry ===================
    def on_load_geometry(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select 3D model", os.getcwd(), "Mesh (*.obj *.stl *.ply *.glb *.gltf)"
        )
        if not path:
            self.logger.log("No file selected.")
            return
        self._load_mesh_from_path(path)

    def _load_mesh_from_path(self, path: str):
        self.logger.log(f"Loading mesh: {path}")
        try:
            m = geometry.load_mesh(path)
            comps = geometry.split_mesh(m)
            parts = [(f"Part_{i}", c) for i, c in enumerate(comps)]

            # Add enclosure if needed
            enabled, mode, pad = self._enclosure_settings()
            parts = add_or_update_enclosure(
                mesh=m,
                parts_named=parts,
                enabled=enabled,
                mode=mode,
                pad_rel=pad,
                force=False,          # normal path respects watertight check
                part_name="Bounds"
            )

            # Set state
            self.state.mesh = m
            self.state.parts = parts
            self.state.assignments.clear()
            self.current_mesh_path = path

            # Ensure & assign Free Space to Bounds if Bounds exists
            if any(n == "Bounds" for n, _ in parts):
                free_name = ensure_free_space_material(self.state.matlib, self.refresh_materials_list, self.logger)
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

    def on_enclosure_now(self):
        if not self.state.mesh:
            self.logger.log("Load a mesh before adding enclosure.", error=True)
            return
        enabled, mode, pad = self._enclosure_settings()
        parts = add_or_update_enclosure(
            mesh=self.state.mesh,
            parts_named=self.state.parts,
            enabled=True,      # force true for manual action
            mode=mode,
            pad_rel=pad,
            force=True,
            part_name="Bounds"
        )
        self.state.parts = parts
        self.refresh_parts_list()
        self._draw()
        free_name = ensure_free_space_material(self.state.matlib, self.refresh_materials_list, self.logger)
        if free_name:
            self.state.assignments["Bounds"] = free_name
            self.logger.log(f'Assigned "{free_name}" → Bounds')
            self.refresh_parts_list()
            self._draw(highlight_name="Bounds")

    def on_part_selected(self, row: int):
        self.state.current_part_index = row
        if 0 <= row < len(self.state.parts):
            self._draw(highlight_name=self.state.parts[row][0])

    def on_mode_changed(self, idx: int):
        if self.state.parts:
            self.logger.log(f"Render mode: {self.combo_mode.currentText()}")
            name = self.state.parts[self.state.current_part_index][0] if 0 <= self.state.current_part_index < len(self.state.parts) else None
            self._draw(highlight_name=name)

    # =================== Materials ===================
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

    def _parts_context_menu(self, pos):
        item = self.parts_list.itemAt(pos)
        if not item:
            return
        menu = QtWidgets.QMenu(self)
        act_assign_fs = menu.addAction('Assign "Free Space" to Bounds')
        action = menu.exec_(self.parts_list.mapToGlobal(pos))
        if action == act_assign_fs:
            # ensure Bounds exists
            if not any(n == "Bounds" for n, _ in self.state.parts):
                self.on_enclosure_now()
            free_name = ensure_free_space_material(self.state.matlib, self.refresh_materials_list, self.logger)
            if free_name:
                self.state.assignments["Bounds"] = free_name
                self.logger.log(f'Assigned "{free_name}" → Bounds')
                self.refresh_parts_list()
                self._draw(highlight_name="Bounds")

    # =================== Project I/O ===================
    def _serialize_project(self) -> dict:
        enabled, mode, pad = self._enclosure_settings()
        return serialize_project(
            mesh_path=self.current_mesh_path,
            assignments=self.state.assignments,
            render_mode=self._current_render_mode(),
            enclosure={"enabled": enabled, "mode": mode, "pad": pad},
            version=1
        )

    def _load_project_dict(self, data: dict):
        # Update UI + state using helper; returns a mesh path to load (if any)
        ui_restore, mesh_path = load_project_into_state(data)
        # Apply UI settings
        self.chk_enclosure.setChecked(ui_restore["enclosure_enabled"])
        self.combo_enclosure_mode.setCurrentText(ui_restore["enclosure_mode_text"])
        self.spin_pad.setValue(ui_restore["enclosure_pad_percent"])
        self.combo_mode.setCurrentText(ui_restore["render_mode_text"])
        # Load mesh if available
        if mesh_path and os.path.exists(mesh_path):
            self._load_mesh_from_path(mesh_path)
        else:
            self.logger.log("Project has no mesh_path or file missing. Load a model manually.", error=True)
        # Apply assignments to existing parts
        applied = 0
        for name, _ in self.state.parts:
            if name in data.get("assignments", {}):
                self.state.assignments[name] = data["assignments"][name]
                applied += 1
        self.logger.log(f"Restored {applied} material assignments from project.")
        self.refresh_parts_list()
        self._draw()

    def new_project(self):
        self.state = ProjectState()
        self.current_project_file = None
        self.current_mesh_path = None
        self.parts_list.clear()
        self.search_mat.clear()
        self.combo_mode.setCurrentText("Shaded")
        self.chk_enclosure.setChecked(True)
        self.combo_enclosure_mode.setCurrentText("AABB (fast)")
        self.spin_pad.setValue(5)
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
        if not path.lower().endswith(".atlasproj.json"):
            path += ".atlasproj.json"
        self.current_project_file = path
        self.save_project()
