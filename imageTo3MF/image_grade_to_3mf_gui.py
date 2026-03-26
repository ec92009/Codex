#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import csv
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt, QProcess, QSize, QTimer, QSettings
from PySide6.QtGui import QColor, QPixmap, QTextCursor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
    QHeaderView,
)
from PIL import Image

import image_grade_to_3mf as engine


PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_PROJECT_DIR = Path("/Users/ecohen/Codex/imageTo3MF")
RUNTIME_PROJECT_DIR = SOURCE_PROJECT_DIR if not (PROJECT_DIR / "image_grade_to_3mf.py").exists() and SOURCE_PROJECT_DIR.exists() else PROJECT_DIR
SCRIPT_PATH = RUNTIME_PROJECT_DIR / "image_grade_to_3mf.py"
PRESET_PATH = RUNTIME_PROJECT_DIR / "material_presets.json"
DEFAULT_FILAMENT_DB_PATH = RUNTIME_PROJECT_DIR.parent / "filamentDB" / "data" / "filaments.tsv"
PROJECT_PYTHON = RUNTIME_PROJECT_DIR / ".venv" / "bin" / "python"
DEFAULT_LONG_SIDE_MM = 100.0
DEFAULT_LONG_SIDE_MM = 100.0


class ImagePreview(QLabel):
    def __init__(self, title: str) -> None:
        super().__init__()
        self._pixmap: Optional[QPixmap] = None
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(QSize(220, 220))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "QLabel { background: #f7f2e9; border: 1px solid #d0c3ae; border-radius: 10px; color: #765f47; }"
        )
        self.setText(title)

    def set_image(self, path: Optional[Path], placeholder: str) -> None:
        if path is None or not path.exists():
            self._pixmap = None
            self.setText(placeholder)
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._pixmap = None
            self.setText(placeholder)
            return
        self._pixmap = pixmap
        self._refresh_pixmap()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._refresh_pixmap()

    def _refresh_pixmap(self) -> None:
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            max(1, self.width() - 16),
            max(1, self.height() - 16),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)


class MaterialRow(QWidget):
    def __init__(self, slot: str, profile: engine.MaterialProfile) -> None:
        super().__init__()
        self.slot = slot
        self.name = profile.name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.slot_label = QLabel(f"Slot {slot}")
        self.slot_label.setFixedWidth(48)
        self.name_label = QLabel(profile.name.capitalize())
        self.name_label.setFixedWidth(72)

        self.hex_edit = QLineEdit(profile.hex_color)
        self.hex_edit.setFixedWidth(90)
        self.hex_edit.textChanged.connect(self._sync_button)

        self.color_button = QPushButton("Color")
        self.color_button.setFixedWidth(70)
        self.color_button.clicked.connect(self.pick_color)

        self.td_spin = QDoubleSpinBox()
        self.td_spin.setRange(0.01, 999.0)
        self.td_spin.setDecimals(2)
        self.td_spin.setSingleStep(0.1)
        self.td_spin.setValue(profile.td)
        self.td_spin.setSuffix(" TD")
        self.td_spin.setFixedWidth(96)

        self.db_button = QPushButton("DB")
        self.db_button.setFixedWidth(42)
        self.db_button.setToolTip("Pick a filament from filamentDB")

        layout.addWidget(self.slot_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.hex_edit)
        layout.addWidget(self.color_button)
        layout.addWidget(self.td_spin)
        layout.addWidget(self.db_button)
        layout.addStretch(1)
        self._sync_button()

    def pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.hex_edit.text()), self, f"Choose {self.name} color")
        if color.isValid():
            self.hex_edit.setText(color.name().upper())

    def _sync_button(self) -> None:
        text = self.hex_edit.text().strip()
        color = QColor(text) if re.fullmatch(r"#[0-9a-fA-F]{6}", text) else QColor("#cccccc")
        self.color_button.setStyleSheet(
            f"QPushButton {{ background: {color.name()}; color: {'#111111' if color.lightness() > 140 else '#fdf8ef'}; }}"
        )

    def set_profile(self, profile: engine.MaterialProfile) -> None:
        self.hex_edit.setText(profile.hex_color)
        self.td_spin.setValue(profile.td)

    def to_argument(self) -> str:
        return f"{self.slot}:{self.hex_edit.text().strip().upper()}@{self.td_spin.value():.2f}"

    def matches_profile(self, profile: engine.MaterialProfile) -> bool:
        return (
            self.hex_edit.text().strip().upper() == profile.hex_color
            and abs(self.td_spin.value() - profile.td) < 1e-9
        )

    def to_json(self) -> Dict[str, str | float]:
        return {
            "slot": self.slot,
            "name": self.name,
            "hex_color": self.hex_edit.text().strip().upper(),
            "td": self.td_spin.value(),
        }

    def apply_db_filament(self, filament_name: str, hex_color: str, td: float) -> None:
        self.hex_edit.setText(hex_color.strip().upper())
        self.td_spin.setValue(td)
        self.db_button.setToolTip(f"{filament_name} | {hex_color.strip().upper()} | {td:.2f} TD")


class FilamentPickerDialog(QDialog):
    def __init__(self, db_path: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Choose Filament from DB")
        self.resize(820, 460)
        self.selected_filament: Optional[dict[str, str | float]] = None

        layout = QVBoxLayout(self)
        help_label = QLabel("Pick a measured filament to fill this material slot.")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ID", "Brand", "Type", "Name", "Color", "HEX", "TD"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(lambda *_: self.accept_selection())
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        use_button = buttons.addButton("Use Selected", QDialogButtonBox.AcceptRole)
        use_button.clicked.connect(self.accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_rows(db_path)

    def _load_rows(self, db_path: Path) -> None:
        if not db_path.exists():
            QMessageBox.information(self, "No DB found", f"filamentDB was not found at {db_path}")
            return
        with db_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            rows = [
                row
                for row in reader
                if row.get("td", "").strip()
            ]
        rows.sort(key=lambda row: int(row["id"]), reverse=True)
        rows = rows[:500]

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row["id"]),
                row["brand"],
                row["filament_type"],
                row["name"],
                "",
                row["color"],
                f"{float(row['td']):.2f}",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.EditRole, int(row["id"]))
                    item.setTextAlignment(Qt.AlignCenter)
                elif column == 6:
                    item.setData(Qt.EditRole, float(row["td"]))
                    item.setTextAlignment(Qt.AlignCenter)
                elif column == 4:
                    color = QColor(str(row["color"]))
                    if color.isValid():
                        item.setBackground(color)
                        item.setToolTip(str(row["color"]))
                self.table.setItem(row_index, column, item)
        if rows:
            self.table.selectRow(0)
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.DescendingOrder)

    def accept_selection(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Nothing selected", "Choose a filament row first.")
            return
        self.selected_filament = {
            "id": self.table.item(row, 0).text(),
            "brand": self.table.item(row, 1).text(),
            "type": self.table.item(row, 2).text(),
            "name": self.table.item(row, 3).text(),
            "hex_color": self.table.item(row, 5).text(),
            "td": float(self.table.item(row, 6).text()),
        }
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("Codex", "LeadLight")
        self.process: Optional[QProcess] = None
        self.input_path: Optional[Path] = None
        self.preview_path: Optional[Path] = None
        self.output_path: Optional[Path] = None
        self.stage_dir: Optional[Path] = None
        self.stage_paths: list[tuple[str, Path]] = []
        self.stage_index: int = -1
        self.source_image_size: Optional[tuple[int, int]] = None
        self.default_profiles = engine.default_material_profiles()
        self.material_rows: Dict[str, MaterialRow] = {}
        self.app_icon_path = RUNTIME_PROJECT_DIR / "leadlight_icon.svg"
        self.filament_db_path = self._load_filament_db_path()

        self.setWindowTitle("LeadLight")
        if self.app_icon_path.exists():
            self.setWindowIcon(QIcon(str(self.app_icon_path)))
        self._build_ui()
        self._apply_style()
        self.reset_materials()
        self._refresh_filament_db_status()
        self._apply_initial_geometry()

    def _load_filament_db_path(self) -> Path:
        raw_path = self.settings.value("filament_db_path", str(DEFAULT_FILAMENT_DB_PATH))
        return Path(str(raw_path)).expanduser()

    def _set_filament_db_path(self, path: Path) -> None:
        resolved = path.expanduser()
        self.filament_db_path = resolved
        self.settings.setValue("filament_db_path", str(resolved))
        self._refresh_filament_db_status()

    def _refresh_filament_db_status(self) -> None:
        if not hasattr(self, "filament_db_status_label"):
            return
        path_text = str(self.filament_db_path)
        if self.filament_db_path.exists():
            self.filament_db_status_label.setText(f"Library: {path_text}")
            self.filament_db_status_label.setStyleSheet("color: #715d49; font-size: 12px;")
        else:
            self.filament_db_status_label.setText(f"Library missing: {path_text}")
            self.filament_db_status_label.setStyleSheet("color: #8c4c2f; font-size: 12px; font-weight: 600;")

    def choose_filament_db_path(self) -> None:
        self._prepare_dialog()
        start_dir = str(self.filament_db_path.parent if self.filament_db_path.parent.exists() else Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose filament TSV library",
            start_dir,
            "TSV Files (*.tsv);;All Files (*)",
        )
        if not path:
            return
        chosen_path = Path(path).expanduser()
        self._set_filament_db_path(chosen_path)
        self.summary_label.setText(f"LeadLight will use filament library:\n{chosen_path}")

    def reset_filament_db_path(self) -> None:
        self._set_filament_db_path(DEFAULT_FILAMENT_DB_PATH)
        self.summary_label.setText(f"LeadLight filament library reset to:\n{DEFAULT_FILAMENT_DB_PATH}")

    def _apply_initial_geometry(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1260, 640)
            return
        available = screen.availableGeometry()
        width = min(1320, max(1080, int(available.width() * 0.88)))
        height = min(660, max(560, int(available.height() * 0.72)))
        self.resize(width, height)
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        QTimer.singleShot(0, self._recenter_on_screen)

    def _recenter_on_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        top_left = frame.topLeft()
        top_left.setY(max(available.top() + 20, top_left.y()))
        self.move(top_left)

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        header = QLabel("LeadLight")
        header.setStyleSheet("font-size: 28px; font-weight: 700; color: #3f2d1d;")
        subheader = QLabel(
            "Build Snapmaker-Orca-ready layered color plates with TD-aware materials and a dedicated black lead cap."
        )
        subheader.setStyleSheet("font-size: 13px; color: #745f49;")

        root_layout.addWidget(header)
        root_layout.addWidget(subheader)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_preview_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([420, 560, 420])

        root_layout.addWidget(splitter, 1)
        footer = QLabel("Dimensions are in millimeters.")
        footer.setStyleSheet("font-size: 11px; color: #8a7763;")
        footer.setAlignment(Qt.AlignRight)
        root_layout.addWidget(footer)
        self.setCentralWidget(root)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        image_group = QGroupBox("Source")
        image_form = QFormLayout(image_group)
        image_form.setHorizontalSpacing(10)
        image_form.setVerticalSpacing(10)
        image_form.setContentsMargins(18, 18, 18, 18)
        image_form.setLabelAlignment(Qt.AlignRight)
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setPlaceholderText("/Users/ecohen/Desktop/image.png")
        browse_button = QPushButton("Choose Image")
        browse_button.clicked.connect(self.choose_image)
        image_row = QWidget()
        image_row_layout = QHBoxLayout(image_row)
        image_row_layout.setContentsMargins(0, 0, 0, 0)
        image_row_layout.addWidget(self.image_path_edit, 1)
        image_row_layout.addWidget(browse_button)
        image_form.addRow("Image", image_row)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional short description")
        image_form.addRow("Description", self.description_edit)

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Optional custom output 3MF path")
        output_button = QPushButton("Browse")
        output_button.clicked.connect(self.choose_output)
        output_row = QWidget()
        output_row_layout = QHBoxLayout(output_row)
        output_row_layout.setContentsMargins(0, 0, 0, 0)
        output_row_layout.addWidget(self.output_edit, 1)
        output_row_layout.addWidget(output_button)
        image_form.addRow("Output", output_row)

        layout.addWidget(image_group)

        settings_group = QGroupBox("Model")
        settings_grid = QGridLayout(settings_group)
        settings_grid.setContentsMargins(18, 18, 18, 18)
        settings_grid.setHorizontalSpacing(12)
        settings_grid.setVerticalSpacing(10)

        self.size_edit = QLineEdit("")
        self.size_edit.setPlaceholderText("Auto from image")
        self.plate_size_edit = QLineEdit("270x270")
        self.plate_size_edit.editingFinished.connect(self._update_size_slider_bounds)
        self.resolution_spin = self._make_mm_spin(0.01, 5.0, engine.DEFAULT_RESOLUTION_MM, 0.05)
        self.layer_height_spin = self._make_mm_spin(0.01, 5.0, engine.DEFAULT_BASE_LAYER_HEIGHT_MM, 0.05)
        self.base_layers_spin = QDoubleSpinBox()
        self.base_layers_spin.setRange(1, 99)
        self.base_layers_spin.setDecimals(0)
        self.base_layers_spin.setValue(engine.DEFAULT_BASE_LAYER_COUNT)
        self.base_layers_spin.setSingleStep(1)
        self.lead_height_spin = self._make_mm_spin(0.0, 10.0, engine.DEFAULT_LEAD_CAP_HEIGHT_MM, 0.05)
        self.lead_thickness_spin = self._make_mm_spin(0.01, 10.0, engine.DEFAULT_LEAD_THICKNESS_MM, 0.05)
        self.lead_mode_combo = QComboBox()
        self.lead_mode_combo.addItems(["generate", "detect"])
        self.seed_spin = QDoubleSpinBox()
        self.seed_spin.setRange(0, 999999)
        self.seed_spin.setDecimals(0)
        self.seed_spin.setValue(7)
        self.seed_spin.setSingleStep(1)

        self.blur_combo = QComboBox()
        self.blur_combo.addItems(["none", "low", "medium", "strong"])

        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(27, 263)
        self.size_slider.setValue(int(DEFAULT_LONG_SIDE_MM))
        self.size_slider.setEnabled(False)
        self.size_slider.valueChanged.connect(self._sync_size_from_slider)
        self.size_slider_label = QLabel("Long side: auto")
        self.size_slider_label.setStyleSheet("color: #715d49; font-size: 12px;")

        size_widget = QWidget()
        size_layout = QVBoxLayout(size_widget)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(4)
        size_layout.addWidget(self.size_edit)
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_slider_label)

        settings_grid.addWidget(QLabel("Picture size"), 0, 0)
        settings_grid.addWidget(size_widget, 0, 1)
        settings_grid.addWidget(QLabel("Plate size"), 1, 0)
        settings_grid.addWidget(self.plate_size_edit, 1, 1)
        settings_grid.addWidget(QLabel("Resolution"), 2, 0)
        settings_grid.addWidget(self.resolution_spin, 2, 1)
        settings_grid.addWidget(QLabel("Layer height"), 3, 0)
        settings_grid.addWidget(self.layer_height_spin, 3, 1)
        settings_grid.addWidget(QLabel("Base layers"), 4, 0)
        settings_grid.addWidget(self.base_layers_spin, 4, 1)
        settings_grid.addWidget(QLabel("Lead layer height"), 5, 0)
        settings_grid.addWidget(self.lead_height_spin, 5, 1)
        settings_grid.addWidget(QLabel("Lead"), 6, 0)
        settings_grid.addWidget(self.lead_mode_combo, 6, 1)
        settings_grid.addWidget(QLabel("Lead thickness"), 7, 0)
        settings_grid.addWidget(self.lead_thickness_spin, 7, 1)
        settings_grid.addWidget(QLabel("Blur"), 8, 0)
        settings_grid.addWidget(self.blur_combo, 8, 1)
        settings_grid.addWidget(QLabel("Seed"), 9, 0)
        settings_grid.addWidget(self.seed_spin, 9, 1)

        layout.addWidget(settings_group)

        run_buttons = QWidget()
        run_buttons_layout = QHBoxLayout(run_buttons)
        run_buttons_layout.setContentsMargins(0, 0, 0, 0)
        run_buttons_layout.setSpacing(12)
        self.generate_button = QPushButton("Generate")
        self.generate_button.setObjectName("primaryButton")
        self.generate_button.clicked.connect(self.run_export)
        self.generate_button.setMinimumHeight(40)
        reveal_button = QPushButton("Reveal")
        reveal_button.clicked.connect(self.reveal_output)
        open_button = QPushButton("Open")
        open_button.clicked.connect(self.open_output_in_orca)
        run_buttons_layout.addWidget(self.generate_button, 1)
        run_buttons_layout.addWidget(reveal_button)
        run_buttons_layout.addWidget(open_button)
        layout.addWidget(run_buttons)

        layout.addStretch(1)
        return panel

    def _build_preview_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        self.original_preview = ImagePreview("Original image preview")
        self.stage_preview = ImagePreview("Preview will appear here")

        original_group = QGroupBox("Original")
        original_layout = QVBoxLayout(original_group)
        original_layout.setContentsMargins(18, 18, 18, 18)
        original_layout.addWidget(self.original_preview)

        stage_group = QGroupBox("Preview")
        stage_layout = QVBoxLayout(stage_group)
        stage_layout.setContentsMargins(18, 18, 18, 18)
        self.progress_label = QLabel("Idle")
        self.progress_label.setObjectName("statusBanner")
        self.stage_caption_label = QLabel("No stage yet")
        self.stage_caption_label.setStyleSheet("color: #715d49;")
        stage_controls = QWidget()
        stage_controls_layout = QHBoxLayout(stage_controls)
        stage_controls_layout.setContentsMargins(0, 0, 0, 0)
        self.stage_prev_button = QPushButton("-")
        self.stage_prev_button.setFixedWidth(36)
        self.stage_prev_button.clicked.connect(lambda: self._step_stage(-1))
        self.stage_next_button = QPushButton("+")
        self.stage_next_button.setFixedWidth(36)
        self.stage_next_button.clicked.connect(lambda: self._step_stage(1))
        self.stage_counter_label = QLabel("0 / 0")
        self.stage_counter_label.setStyleSheet("color: #715d49;")
        stage_controls_layout.addWidget(self.stage_prev_button)
        stage_controls_layout.addWidget(self.stage_next_button)
        stage_controls_layout.addWidget(self.stage_counter_label)
        stage_controls_layout.addStretch(1)
        stage_layout.addWidget(self.progress_label)
        stage_layout.addWidget(self.stage_caption_label)
        stage_layout.addWidget(stage_controls)
        stage_layout.addWidget(self.stage_preview)

        layout.addWidget(original_group, 1)
        layout.addWidget(stage_group, 2)
        self._update_stage_controls()
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        materials_group = QGroupBox("Materials")
        materials_layout = QVBoxLayout(materials_group)
        materials_layout.setSpacing(10)
        materials_layout.setContentsMargins(18, 18, 18, 18)
        materials_help = QLabel("Use measured TD values when you have them. Leave untouched to use the built-in CMYWK defaults.")
        materials_help.setWordWrap(True)
        materials_help.setStyleSheet("color: #715d49;")
        materials_layout.addWidget(materials_help)

        library_row = QWidget()
        library_row_layout = QHBoxLayout(library_row)
        library_row_layout.setContentsMargins(0, 0, 0, 0)
        library_row_layout.setSpacing(8)
        self.filament_db_status_label = QLabel("")
        self.filament_db_status_label.setWordWrap(True)
        settings_button = QPushButton("...")
        settings_button.setFixedWidth(36)
        settings_button.clicked.connect(self.choose_filament_db_path)
        reset_library_button = QPushButton("Default")
        reset_library_button.clicked.connect(self.reset_filament_db_path)
        library_row_layout.addWidget(self.filament_db_status_label, 1)
        library_row_layout.addWidget(settings_button)
        library_row_layout.addWidget(reset_library_button)
        materials_layout.addWidget(library_row)

        for slot in ("1", "2", "3", "4", "5"):
            row = MaterialRow(slot, self.default_profiles[slot])
            row.db_button.clicked.connect(lambda _=False, slot_key=slot: self.pick_material_from_db(slot_key))
            self.material_rows[slot] = row
            materials_layout.addWidget(row)

        materials_buttons = QWidget()
        materials_buttons_layout = QHBoxLayout(materials_buttons)
        materials_buttons_layout.setContentsMargins(0, 0, 0, 0)
        materials_buttons_layout.setSpacing(12)
        cmywk_button = QPushButton("CMYWK")
        cmywk_button.clicked.connect(self.reset_materials)
        rgbwk_button = QPushButton("RGBWK")
        rgbwk_button.clicked.connect(self.set_rgbwk_materials)
        regen_button = QPushButton("Regen")
        regen_button.clicked.connect(self.run_export)
        save_button = QPushButton("Save Preset")
        save_button.clicked.connect(self.save_preset)
        load_button = QPushButton("Load Preset")
        load_button.clicked.connect(self.load_preset)
        materials_buttons_layout.addWidget(cmywk_button)
        materials_buttons_layout.addWidget(rgbwk_button)
        materials_buttons_layout.addWidget(regen_button)
        materials_buttons_layout.addWidget(save_button)
        materials_buttons_layout.addWidget(load_button)
        materials_buttons_layout.addStretch(1)
        materials_layout.addWidget(materials_buttons)

        summary_group = QGroupBox("Status")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setContentsMargins(18, 18, 18, 18)
        self.summary_label = QLabel("Choose an image and generate a 3MF.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setObjectName("statusBanner")
        summary_layout.addWidget(self.summary_label)

        log_group = QGroupBox("Run Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(18, 18, 18, 18)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)

        layout.addWidget(materials_group, 0)
        layout.addWidget(summary_group, 0)
        layout.addWidget(log_group, 1)
        return panel

    def pick_material_from_db(self, slot: str) -> None:
        if not self.filament_db_path.exists():
            answer = QMessageBox.question(
                self,
                "Filament library not found",
                f"LeadLight could not find the filament TSV at:\n{self.filament_db_path}\n\nChoose a different TSV now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.choose_filament_db_path()
            return

        dialog = FilamentPickerDialog(self.filament_db_path, self)
        if dialog.exec() != QDialog.Accepted or dialog.selected_filament is None:
            return
        selected = dialog.selected_filament
        self.material_rows[slot].apply_db_filament(
            f"{selected['brand']} {selected['type']} {selected['name']}",
            str(selected["hex_color"]),
            float(selected["td"]),
        )
        self.summary_label.setText(
            f"Slot {slot} now uses {selected['brand']} {selected['type']} {selected['name']} from filamentDB."
        )

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #efe6d8;
                color: #2f241a;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #d0c3ae;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 12px;
                background: #fbf7f0;
                font-weight: 600;
            }
            QGroupBox::title {
                left: 12px;
                padding: 0 6px;
                color: #584635;
            }
            QLabel {
                color: #2f241a;
            }
            QLineEdit, QTextEdit, QComboBox, QDoubleSpinBox {
                background: #fffdfa;
                border: 1px solid #cfbfa7;
                border-radius: 8px;
                padding: 6px 8px;
                selection-background-color: #0a84ff;
                placeholder-text-color: #9a866f;
            }
            QTextEdit {
                color: #493726;
            }
            QSlider::groove:horizontal {
                border: 1px solid #cfbfa7;
                height: 6px;
                background: #eadbc8;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #0a84ff;
                border: none;
                width: 18px;
                margin: -7px 0;
                border-radius: 9px;
            }
            QPushButton {
                background: #b56f38;
                color: #fffaf4;
                border: none;
                border-radius: 9px;
                padding: 8px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #a55f2d;
            }
            QPushButton#primaryButton {
                background: #0a84ff;
            }
            QPushButton#primaryButton:hover {
                background: #2b95ff;
            }
            QPushButton:disabled {
                background: #d5c8b7;
                color: #f4efe8;
                border: 1px solid #d9cdbf;
            }
            QCheckBox {
                spacing: 8px;
            }
            QLabel#statusBanner {
                background: #efe1cf;
                border: 1px solid #d5c2a5;
                border-radius: 8px;
                padding: 10px 12px;
                color: #6a4b2d;
                font-weight: 600;
            }
            """
        )

    def _make_mm_spin(self, minimum: float, maximum: float, value: float, step: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(2)
        spin.setValue(value)
        spin.setSingleStep(step)
        return spin

    def _prepare_dialog(self) -> None:
        self.raise_()
        self.activateWindow()

    def choose_image(self) -> None:
        self._prepare_dialog()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose image",
            str(Path.home() / "Desktop"),
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)",
        )
        if not path:
            return
        self.input_path = Path(path)
        self.image_path_edit.setText(path)
        self.original_preview.set_image(self.input_path, "Original image preview")
        self._sync_size_from_image(self.input_path)

    def choose_output(self) -> None:
        self._prepare_dialog()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose output 3MF path",
            str(RUNTIME_PROJECT_DIR / "out" / "output.3mf"),
            "3MF Files (*.3mf)",
        )
        if path:
            self.output_edit.setText(path)

    def reset_materials(self) -> None:
        for slot, row in self.material_rows.items():
            row.set_profile(self.default_profiles[slot])

    def _suggest_model_size(self, image_path: Path, long_side_mm: float = DEFAULT_LONG_SIDE_MM) -> str:
        with Image.open(image_path) as image:
            width_px, height_px = image.size
        self.source_image_size = (width_px, height_px)
        if width_px <= 0 or height_px <= 0:
            return "100x100"
        long_side = max(width_px, height_px)
        scale = long_side_mm / float(long_side)
        width_mm = width_px * scale
        height_mm = height_px * scale
        return f"{engine.format_number(width_mm)}x{engine.format_number(height_mm)}"

    def _sync_size_from_image(self, image_path: Path) -> None:
        try:
            self._update_size_slider_bounds()
            self.size_slider.blockSignals(True)
            self.size_slider.setEnabled(True)
            current_value = min(max(int(DEFAULT_LONG_SIDE_MM), self.size_slider.minimum()), self.size_slider.maximum())
            self.size_slider.setValue(current_value)
            self.size_slider.blockSignals(False)
            self.size_edit.setText(self._suggest_model_size(image_path, long_side_mm=float(self.size_slider.value())))
            self.size_slider_label.setText(f"Long side: {self.size_slider.value()} mm")
        except Exception:
            self.source_image_size = None
            self.size_slider.setEnabled(False)
            self.size_slider_label.setText("Long side: auto")

    def _sync_size_from_slider(self, value: int) -> None:
        if self.input_path is None or self.source_image_size is None:
            self.size_slider_label.setText("Long side: auto")
            return
        self.size_edit.setText(self._suggest_model_size(self.input_path, long_side_mm=float(value)))
        self.size_slider_label.setText(f"Long side: {value} mm")

    def _update_size_slider_bounds(self) -> None:
        try:
            plate_width, plate_height = engine.parse_mm_pair(self.plate_size_edit.text().strip() or "270x270")
        except Exception:
            plate_width, plate_height = 270.0, 270.0

        min_long_side = max(1, int(min(plate_width, plate_height) / 10.0))
        max_long_side = int(max(1.0, min(plate_width, plate_height) - 7.0))

        if self.source_image_size is not None:
            width_px, height_px = self.source_image_size
            long_px = max(width_px, height_px)
            if long_px > 0:
                scale_limit = min((plate_width - 7.0) / width_px, (plate_height - 7.0) / height_px)
                max_long_side = int(max(1.0, long_px * scale_limit))

        max_long_side = max(min_long_side, max_long_side)
        current_value = self.size_slider.value()
        self.size_slider.blockSignals(True)
        self.size_slider.setRange(min_long_side, max_long_side)
        self.size_slider.setValue(min(max(current_value, min_long_side), max_long_side))
        self.size_slider.blockSignals(False)
        if self.source_image_size is not None and self.input_path is not None:
            self._sync_size_from_slider(self.size_slider.value())

    def set_rgbwk_materials(self) -> None:
        rgbwk_profiles = {
            "1": engine.MaterialProfile(slot="1", name="red", hex_color="#FF0000", rgb=(255, 0, 0), td=5.5),
            "2": engine.MaterialProfile(slot="2", name="green", hex_color="#00FF00", rgb=(0, 255, 0), td=5.5),
            "3": engine.MaterialProfile(slot="3", name="blue", hex_color="#0000FF", rgb=(0, 0, 255), td=5.5),
            "4": engine.MaterialProfile(slot="4", name="white", hex_color="#FFFFFF", rgb=(255, 255, 255), td=9.0),
            "5": engine.MaterialProfile(slot="5", name="black", hex_color="#000000", rgb=(0, 0, 0), td=0.15),
        }
        for slot, row in self.material_rows.items():
            row.set_profile(rgbwk_profiles[slot])

    def save_preset(self) -> None:
        self._prepare_dialog()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save material preset",
            str(PRESET_PATH),
            "JSON Files (*.json)",
        )
        if not path:
            return
        payload = [row.to_json() for row in self.material_rows.values()]
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.summary_label.setText(f"Saved material preset to {path}")

    def load_preset(self) -> None:
        self._prepare_dialog()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load material preset",
            str(PRESET_PATH if PRESET_PATH.exists() else RUNTIME_PROJECT_DIR),
            "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            for entry in payload:
                slot = str(entry["slot"])
                if slot not in self.material_rows:
                    continue
                parsed_hex, rgb = engine.parse_hex_color(str(entry["hex_color"]))
                profile = engine.MaterialProfile(
                    slot=slot,
                    name=str(entry.get("name", self.default_profiles[slot].name)),
                    hex_color=parsed_hex,
                    rgb=rgb,
                    td=float(entry["td"]),
                )
                self.material_rows[slot].set_profile(profile)
            self.summary_label.setText(f"Loaded material preset from {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Preset error", f"Could not load preset:\n{exc}")

    def _effective_image_path(self) -> Optional[Path]:
        raw = self.image_path_edit.text().strip()
        if not raw:
            return None
        return Path(raw).expanduser()

    def _material_args(self) -> list[str]:
        args: list[str] = []
        for slot, row in self.material_rows.items():
            if not row.matches_profile(self.default_profiles[slot]):
                args.extend(["--material", row.to_argument()])
        return args

    def _export_launcher(self, script_args: list[str]) -> tuple[str, list[str]]:
        if PROJECT_PYTHON.exists():
            return str(PROJECT_PYTHON), ["-u", str(SCRIPT_PATH), *script_args]
        if getattr(sys, "frozen", False):
            uv_path = shutil.which("uv") or "/opt/homebrew/bin/uv"
            if Path(uv_path).exists():
                return (
                    uv_path,
                    ["run", "--project", str(RUNTIME_PROJECT_DIR), "python", "-u", str(SCRIPT_PATH), *script_args],
                )
            python_path = shutil.which("python3")
            if python_path:
                return python_path, ["-u", str(SCRIPT_PATH), *script_args]
            raise RuntimeError("Could not find uv or python3 to launch the exporter from the app bundle.")
        if shutil.which(sys.executable):
            return sys.executable, ["-u", str(SCRIPT_PATH), *script_args]
        uv_path = shutil.which("uv") or "/opt/homebrew/bin/uv"
        if Path(uv_path).exists():
            return uv_path, ["run", "--project", str(RUNTIME_PROJECT_DIR), "python", "-u", str(SCRIPT_PATH), *script_args]
        raise RuntimeError("Could not find a working Python launcher for the exporter.")

    def run_export(self) -> None:
        image_path = self._effective_image_path()
        if image_path is None:
            QMessageBox.information(self, "Image required", "Choose an image before generating a 3MF.")
            return
        if not image_path.exists():
            QMessageBox.warning(self, "Missing image", f"Image not found:\n{image_path}")
            return

        self.input_path = image_path
        if not self.size_edit.text().strip():
            self._sync_size_from_image(image_path)
        self.original_preview.set_image(image_path, "Original image preview")
        self.stage_preview.set_image(None, "Preview will appear here")
        self.preview_path = None
        self.output_path = None
        self.stage_paths = []
        self.stage_index = -1
        self.stage_dir = Path(tempfile.mkdtemp(prefix="leadlight_stages_"))
        self.stage_caption_label.setText("Waiting for stages...")
        self.stage_counter_label.setText("0 / 0")
        self._update_stage_controls()

        script_args = [
            str(image_path),
            "--size",
            self.size_edit.text().strip() or self._suggest_model_size(image_path, long_side_mm=float(self.size_slider.value())),
            "--plate-size",
            self.plate_size_edit.text().strip() or "270x270",
            "--resolution",
            f"{self.resolution_spin.value():.2f}mm",
            "--layer-height",
            f"{self.layer_height_spin.value():.2f}mm",
            "--base-layers",
            str(int(self.base_layers_spin.value())),
            "--lead-height",
            f"{self.lead_height_spin.value():.2f}mm",
            "--lead-source",
            self.lead_mode_combo.currentText(),
            "--lead-thickness",
            f"{self.lead_thickness_spin.value():.2f}mm",
            "--blur",
            self.blur_combo.currentText(),
            "--seed",
            str(int(self.seed_spin.value())),
            "--stage-dir",
            str(self.stage_dir),
        ]

        description = self.description_edit.text().strip()
        if description:
            script_args.extend(["--description", description])

        output_path = self.output_edit.text().strip()
        if output_path:
            script_args.extend(["--output", output_path])

        script_args.append("--no-open")

        script_args.extend(self._material_args())

        self.log_view.clear()
        self.summary_label.setText("Generating 3MF...")
        self.progress_label.setText("Generating 3MF...")
        self.generate_button.setEnabled(False)

        try:
            program, process_args = self._export_launcher(script_args)
        except RuntimeError as exc:
            self.generate_button.setEnabled(True)
            self.summary_label.setText(str(exc))
            QMessageBox.critical(self, "Export launcher error", str(exc))
            return

        process = QProcess(self)
        process.setProgram(program)
        process.setArguments(process_args)
        process.setWorkingDirectory(str(RUNTIME_PROJECT_DIR))
        process.setProcessChannelMode(QProcess.MergedChannels)
        process.readyReadStandardOutput.connect(self._append_process_output)
        process.errorOccurred.connect(self._process_error)
        process.finished.connect(self._process_finished)
        self.process = process
        process.start()
        if not process.waitForStarted(3000):
            self._process_error(process.error())

    def _append_process_output(self) -> None:
        if self.process is None:
            return
        chunk = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if not chunk:
            return
        self.log_view.moveCursor(QTextCursor.End)
        self.log_view.insertPlainText(chunk)
        self.log_view.moveCursor(QTextCursor.End)
        self._ingest_stage_lines(chunk)

    def _process_error(self, error) -> None:
        if self.process is None:
            return
        message = f"Could not start export process ({error})."
        stderr_text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if stderr_text:
            self.log_view.moveCursor(QTextCursor.End)
            self.log_view.insertPlainText(stderr_text)
            self.log_view.moveCursor(QTextCursor.End)
        self.generate_button.setEnabled(True)
        self.summary_label.setText(message)
        self.progress_label.setText("Failed")
        self.process = None
        QMessageBox.critical(self, "Export launcher error", message)

    def _process_finished(self, exit_code: int, _status) -> None:
        self.generate_button.setEnabled(True)
        log_text = self.log_view.toPlainText()
        self.preview_path = self._extract_path(log_text, "Preview PNG:")
        self.output_path = self._extract_path(log_text, "3MF output:")
        if exit_code == 0:
            summary = "3MF generated successfully."
            if self.output_path is not None:
                summary += f"\nOutput: {self.output_path}"
            if self.preview_path is not None:
                summary += f"\nPreview: {self.preview_path}"
            self.summary_label.setText(summary)
            self.progress_label.setText("Done")
            if self.stage_paths:
                self._set_stage_index(len(self.stage_paths) - 1)
        else:
            self.summary_label.setText("Generation failed. See the run log for details.")
            self.progress_label.setText("Failed")
            QMessageBox.warning(self, "Generation failed", "The export did not complete successfully. See the run log.")
        self.process = None

    def _ingest_stage_lines(self, text: str) -> None:
        pattern = re.compile(r"^Stage preview\s+(\d+):\s+(.+?):\s+(.*)$", re.MULTILINE)
        for match in pattern.finditer(text):
            name = match.group(2).strip()
            path = Path(match.group(3).strip())
            if any(existing_path == path for _existing_name, existing_path in self.stage_paths):
                continue
            self.stage_paths.append((name, path))
            self._set_stage_index(len(self.stage_paths) - 1)

    def _set_stage_index(self, index: int) -> None:
        if not self.stage_paths:
            self.stage_index = -1
            self.stage_preview.set_image(None, "Preview will appear here")
            self.stage_caption_label.setText("No stage yet")
            self.stage_counter_label.setText("0 / 0")
            self._update_stage_controls()
            return
        self.stage_index = max(0, min(index, len(self.stage_paths) - 1))
        name, path = self.stage_paths[self.stage_index]
        self.stage_preview.set_image(path, "Preview will appear here")
        self.stage_caption_label.setText(name.replace("_", " "))
        self.stage_counter_label.setText(f"{self.stage_index + 1} / {len(self.stage_paths)}")
        self._update_stage_controls()

    def _step_stage(self, delta: int) -> None:
        if not self.stage_paths:
            return
        self._set_stage_index(self.stage_index + delta)

    def _update_stage_controls(self) -> None:
        has_stages = bool(self.stage_paths)
        self.stage_prev_button.setEnabled(has_stages and self.stage_index > 0)
        self.stage_next_button.setEnabled(has_stages and self.stage_index < len(self.stage_paths) - 1)

    def _extract_path(self, text: str, prefix: str) -> Optional[Path]:
        pattern = re.compile(rf"^{re.escape(prefix)}\s+(.*)$", re.MULTILINE)
        match = pattern.search(text)
        if not match:
            return None
        return Path(match.group(1).strip())

    def reveal_output(self) -> None:
        target = self.output_path or self.preview_path
        if target is None:
            QMessageBox.information(self, "No output yet", "Generate something first.")
            return
        subprocess.run(["open", "-R", str(target)], check=False)

    def open_output_in_orca(self) -> None:
        if self.output_path is None:
            QMessageBox.information(self, "No output yet", "Generate a 3MF first.")
            return
        if not self.output_path.exists():
            QMessageBox.warning(self, "Missing output", f"Output not found:\n{self.output_path}")
            return
        if not engine.open_in_orca_slicer(self.output_path):
            QMessageBox.warning(
                self,
                "Could not open Snapmaker Orca",
                f"LeadLight could not open {self.output_path.name} in Snapmaker Orca automatically.",
            )


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LeadLight")
    app.setApplicationDisplayName("LeadLight")
    app.setOrganizationName("Codex")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
