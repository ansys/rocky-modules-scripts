"""
Creates the Graphical User Interface
"""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox, QPushButton, QDialog, QMainWindow,
    QVBoxLayout, QWidget, QFormLayout, QComboBox, QHBoxLayout, QLabel
)
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPixmap,
    QLinearGradient,
    QPen
)

from . import processes
from .color_scale_manager import ColorScaleManager


class GraphicalUserInterface(QMainWindow):

    def __init__(self, app):
        self.presets_folder = Path(__file__).parent.joinpath("colorpresets")
        self.filename = Path(__file__).parent.joinpath("selected_fields.txt")

        super().__init__(None)
        self.app = app

        # state
        self.process = None
        self.new_colors = None

        # performance cache
        self.cs_manager = ColorScaleManager(self.app)
        self._last_process = None
        self._last_gf = None

        self.widget_main = QDialog()
        self.widget_main.setWindowFlags(Qt.WindowCloseButtonHint)
        self.widget_main.setWindowTitle('Custom Color Scale')
        self.widget_main.setFixedSize(350, 300)

        self.layout_main = QVBoxLayout(self)
        self.widget_main.setLayout(self.layout_main)

        self._CreateUI()

        self.widget_main.exec()

    # -----------------------
    # APPLY (OPTIMIZED)
    # -----------------------
    def color_scale_manager_call(self):
        if not self.process:
            return

        gf = self.get_gf_button.currentText()
        if not gf or not self.new_colors:
            return

        # Only update what changed
        if self.process != self._last_process:
            self.cs_manager.set_process(self.process.subject)
            self._last_process = self.process

        if gf != self._last_gf:
            self.cs_manager.set_gf_semantic_association_and_data(
                gf, self.app)
            self._last_gf = gf

        # Always update colors
        self.cs_manager.set_colors(self.new_colors)

    # -----------------------
    # LOAD / SAVE
    # -----------------------
    def load_selections_from_file(self):
        try:
            with open(self.filename, "r", encoding="UTF8") as file:
                lines = file.readlines()

            selected_scope = lines[0].strip()
            selected_gf = lines[1].strip()
            selected_cs = lines[2].strip()

            # Scope
            idx = self.get_process_button.findText(selected_scope)
            if idx != -1:
                self.get_process_button.setCurrentIndex(idx)
                self._on_process_changed(selected_scope)

            # GF
            idx = self.get_gf_button.findText(selected_gf)
            if idx != -1:
                self.get_gf_button.setCurrentIndex(idx)
                self._on_gf_changed(selected_gf)

            # CS
            idx = self.get_cs_button.findText(selected_cs)
            if idx != -1:
                self.get_cs_button.setCurrentIndex(idx)
                self._on_color_scale_changed(selected_cs)

            print("Loaded from file")

        except Exception as e:
            print("Load failed:", e)

    def save_selection_to_file(self):
        with open(self.filename, "w", encoding="UTF8") as file:
            file.write(self.get_process_button.currentText() + "\n")
            file.write(self.get_gf_button.currentText() + "\n")
            file.write(self.get_cs_button.currentText())

        print("Saved")

    # -----------------------
    # HANDLERS
    # -----------------------
    def _on_process_changed(self, key):
        data = processes.rocky_processes(
            self.app, self.presets_folder, key)

        self.process = data["process"]

        if self.process is None:
            self.get_gf_button.setEnabled(False)
            self.get_cs_button.setEnabled(False)

            self.get_gf_button.clear()
            self.get_cs_button.clear()

            self.new_colors = None
            self._clear_preview()
            return

        self.get_gf_button.setEnabled(True)
        self.get_cs_button.setEnabled(True)

        # reset cached state
        self._last_process = None
        self._last_gf = None

        # GF
        self.get_gf_button.blockSignals(True)
        self.get_gf_button.clear()
        self.get_gf_button.addItems([""] + data["gfs"])
        self.get_gf_button.setCurrentIndex(0)
        self.get_gf_button.blockSignals(False)

        # CS
        self.get_cs_button.blockSignals(True)
        self.get_cs_button.clear()
        self.get_cs_button.addItems([""] + data["color_scales"])
        self.get_cs_button.setCurrentIndex(0)
        self.get_cs_button.blockSignals(False)

        self.new_colors = None
        self._clear_preview()

    def _on_gf_changed(self, gf):
        if not gf:
            self.get_cs_button.setCurrentIndex(0)

            self.new_colors = None
            self._clear_preview()

    def _on_color_scale_changed(self, selected):
        self.new_colors = processes.set_color_scale(
            self.presets_folder, selected
        )

        if self.new_colors is None:
            self._clear_preview()
            return

        self._update_preview()

    # -----------------------
    # UI CREATION
    # -----------------------
    def _CreateUI(self):
        self.widget_main.setContentsMargins(5, 5, 5, 5)
        self.layout_main.setContentsMargins(5, 5, 5, 5)

        self.buttons_widget = QWidget()
        self.layout_box = QVBoxLayout()
        self.h_layout_box = QHBoxLayout()

        self.box_button_options = QGroupBox('Options')
        self.v_button_layout = QVBoxLayout()

        # Scope
        self.get_process_button = QComboBox()
        processes_dict = processes.get_available_processes(self.app)

        self.get_process_button.addItems(
            [""] + sorted(processes_dict.keys()))
        self.get_process_button.currentTextChanged.connect(
            self._on_process_changed)

        # GF
        self.get_gf_button = QComboBox()
        self.get_gf_button.setEnabled(False)
        self.get_gf_button.currentTextChanged.connect(self._on_gf_changed)

        # CS
        self.get_cs_button = QComboBox()
        self.get_cs_button.setEnabled(False)
        self.get_cs_button.currentTextChanged.connect(
            self._on_color_scale_changed)

        # Form
        form = QFormLayout()
        form.addRow("Scope", self.get_process_button)
        form.addRow("Grid Function", self.get_gf_button)
        form.addRow("Color Scale", self.get_cs_button)

        self.v_button_layout.addLayout(form)

        # Preview
        self.cs_preview = QGroupBox("Color Scale Preview")

        self.preview_label = QLabel()
        self.preview_label.setFixedSize(270, 30)
        self.preview_label.setScaledContents(False)

        preview_layout = QHBoxLayout()
        # preview_layout.setContentsMargins(10, 5, 10, 5)

        preview_layout.addStretch()
        preview_layout.addWidget(self.preview_label)
        preview_layout.addStretch()

        self.cs_preview.setLayout(preview_layout)

        self.v_button_layout.addWidget(self.cs_preview)

        # Apply
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.color_scale_manager_call)
        self.apply_button.clicked.connect(self.save_selection_to_file)

        self.v_button_layout.addWidget(self.apply_button)

        self.box_button_options.setLayout(self.v_button_layout)
        self.h_layout_box.addWidget(self.box_button_options)

        self.layout_box.addLayout(self.h_layout_box)
        self.buttons_widget.setLayout(self.layout_box)
        self.layout_main.addWidget(self.buttons_widget)

        self.load_selections_from_file()

    # -----------------------
    # HELPERS
    # -----------------------
    def _clear_preview(self):
        self.preview_label.setPixmap(QPixmap())
        
    def _update_preview(self):
        if not self.new_colors:
            self._clear_preview()
            return

        width = 270
        height = 30

        pixmap = QPixmap(width, height)
        pixmap.fill(self.preview_label.palette().window().color())

        gradient = QLinearGradient(0, 0, width, 0)

        for scalar, (r, g, b) in self.new_colors:
            gradient.setColorAt(
                float(scalar),
                QColor.fromRgbF(float(r), float(g), float(b))
            )

        painter = QPainter(pixmap)
        painter.fillRect(pixmap.rect(), gradient)

        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawRect(
            pixmap.rect().adjusted(0, 0, -1, -1)
        )

        painter.end()

        self.preview_label.setPixmap(pixmap)