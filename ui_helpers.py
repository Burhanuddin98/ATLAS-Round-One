# ui_helpers.py — build dock widgets for ATLAS
from PySide6 import QtWidgets, QtCore
from materials_plot import MatPlotMini

# ui_helpers.py (modify make_geometry_dock signature + body)

from PySide6 import QtWidgets, QtCore
from materials_plot import MatPlotMini

def make_geometry_dock(parent, on_load_geometry, on_mode_changed, on_part_selected, on_enclosure_now=None):
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)

    btn_load = QtWidgets.QPushButton("Load 3D Model…")
    btn_load.clicked.connect(on_load_geometry)

    combo_mode = QtWidgets.QComboBox()
    combo_mode.addItems(["Shaded", "Wireframe"])
    combo_mode.currentIndexChanged.connect(on_mode_changed)

    chk_enclosure = QtWidgets.QCheckBox("Auto add bounding box if not watertight")
    chk_enclosure.setChecked(True)

    combo_enclosure_mode = QtWidgets.QComboBox()
    combo_enclosure_mode.addItems(["AABB (fast)", "OBB (tight)"])

    row_pad = QtWidgets.QHBoxLayout()
    row_pad.addWidget(QtWidgets.QLabel("Pad (%)"))
    spin_pad = QtWidgets.QSpinBox()
    spin_pad.setRange(0, 100)
    spin_pad.setValue(5)
    row_pad.addWidget(spin_pad)
    row_pad.addStretch(1)

    btn_enclosure_now = QtWidgets.QPushButton("Add/Update Enclosure Now")
    if on_enclosure_now is not None:
        btn_enclosure_now.clicked.connect(on_enclosure_now)

    parts_list = QtWidgets.QListWidget()
    parts_list.currentRowChanged.connect(on_part_selected)
    parts_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    layout.addWidget(btn_load)
    layout.addWidget(QtWidgets.QLabel("Render Mode"))
    layout.addWidget(combo_mode)

    layout.addSpacing(8)
    layout.addWidget(QtWidgets.QLabel("Enclosure"))
    layout.addWidget(chk_enclosure)
    layout.addWidget(combo_enclosure_mode)
    layout.addLayout(row_pad)
    layout.addWidget(btn_enclosure_now)

    layout.addSpacing(8)
    layout.addWidget(QtWidgets.QLabel("Parts"))
    layout.addWidget(parts_list, 1)

    dock = QtWidgets.QDockWidget("Geometry", parent)
    dock.setWidget(widget)
    dock.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFloatable)
    parent.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)

    return dock, combo_mode, parts_list, chk_enclosure, combo_enclosure_mode, spin_pad, btn_enclosure_now

def make_materials_dock(parent, on_search, on_material_selected, on_assign):
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)

    search = QtWidgets.QLineEdit()
    search.setPlaceholderText("Search materials…")
    search.textChanged.connect(on_search)

    materials_list = QtWidgets.QListWidget()
    materials_list.currentRowChanged.connect(on_material_selected)
    materials_list.itemDoubleClicked.connect(on_assign)

    plot = MatPlotMini()
    btn_assign = QtWidgets.QPushButton("Assign to Selected Part")
    btn_assign.clicked.connect(on_assign)

    layout.addWidget(search)
    layout.addWidget(materials_list, 2)
    layout.addWidget(plot, 1)
    layout.addWidget(btn_assign)

    dock = QtWidgets.QDockWidget("Materials", parent)
    dock.setWidget(widget)
    dock.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFloatable)
    parent.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

    return dock, search, materials_list, plot


def make_log_dock(parent):
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)

    text_box = QtWidgets.QPlainTextEdit()
    text_box.setReadOnly(True)
    text_box.setMaximumBlockCount(4000)

    layout.addWidget(QtWidgets.QLabel("Log"))
    layout.addWidget(text_box, 1)

    dock = QtWidgets.QDockWidget("Log", parent)
    dock.setWidget(widget)
    dock.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFloatable)
    parent.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock)

    return dock, text_box
