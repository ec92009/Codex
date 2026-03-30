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

import numpy as np
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
    QScrollArea,
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
from PIL import Image, ImageEnhance, ImageFilter, ImageQt

import image_grade_to_3mf as engine


PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_PROJECT_DIR = Path.home() / "Codex" / "imageTo3MF"
RUNTIME_PROJECT_DIR = SOURCE_PROJECT_DIR if not (PROJECT_DIR / "image_grade_to_3mf.py").exists() and SOURCE_PROJECT_DIR.exists() else PROJECT_DIR
SCRIPT_PATH = RUNTIME_PROJECT_DIR / "image_grade_to_3mf.py"
PRESET_PATH = RUNTIME_PROJECT_DIR / "material_presets.json"
DEFAULT_FILAMENT_DB_PATH = RUNTIME_PROJECT_DIR.parent / "filamentDB" / "data" / "filaments.tsv"
PROJECT_PYTHON = RUNTIME_PROJECT_DIR / ".venv" / "bin" / "python"
DEFAULT_LONG_SIDE_MM = 100.0
DEFAULT_LONG_SIDE_MM = 100.0
PREVIEW_RENDER_MAX_SIDE_PX = 900
DEFAULT_GUI_NUM_NUANCES = 8


class ImagePreview(QLabel):
    def __init__(self, title: str) -> None:
        super().__init__()
        self._pixmap: Optional[QPixmap] = None
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(QSize(180, 140))
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

    def set_pil_image(self, image: Optional[Image.Image], placeholder: str) -> None:
        if image is None:
            self._pixmap = None
            self.setText(placeholder)
            return
        pixmap = QPixmap.fromImage(ImageQt.ImageQt(image.convert("RGBA")))
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


class NaturalScrollTextEdit(QTextEdit):
    def wheelEvent(self, event) -> None:  # type: ignore[override]  # pragma: no cover - UI path
        super().wheelEvent(event)


class CollapsibleSection(QWidget):
    def __init__(self, title: str, content: QWidget, expanded: bool = True, on_toggle=None) -> None:
        super().__init__()
        self.content = content
        self._on_toggle = on_toggle

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.toggle_button = QPushButton()
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(expanded)
        self.toggle_button.setStyleSheet(
            "QPushButton { text-align: left; font-weight: 600; font-size: 18px; padding: 10px 12px; }"
        )
        self.toggle_button.clicked.connect(self._update_state)

        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content)
        self._title = title
        self._update_state()

    def _update_state(self) -> None:
        expanded = self.toggle_button.isChecked()
        self.content.setVisible(expanded)
        chevron = "▼" if expanded else "▶"
        self.toggle_button.setText(f"{chevron} {self._title}")
        if self._on_toggle is not None:
            self._on_toggle(expanded)


class MaterialRow(QWidget):
    def __init__(self, slot: str, profile: engine.MaterialProfile) -> None:
        super().__init__()
        self.slot = slot
        self.name = profile.name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.slot_name_label = QLabel(f"{slot}. {profile.name.capitalize()}")
        self.slot_name_label.setMinimumWidth(78)
        self.slot_name_label.setMaximumWidth(96)

        self.hex_edit = QLineEdit(profile.hex_color)
        self.hex_edit.setMinimumWidth(108)
        self.hex_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.hex_edit.textChanged.connect(self._sync_button)

        self.color_button = QPushButton("")
        self.color_button.setToolTip("Choose color")
        self.color_button.setFixedWidth(34)
        self.color_button.clicked.connect(self.pick_color)

        self.td_spin = QDoubleSpinBox()
        self.td_spin.setRange(0.01, 999.0)
        self.td_spin.setDecimals(2)
        self.td_spin.setSingleStep(0.1)
        self.td_spin.setValue(profile.td)
        self.td_spin.setSuffix(" TD")
        self.td_spin.setFixedWidth(92)

        self.db_button = QPushButton("DB")
        self.db_button.setFixedWidth(46)
        self.db_button.setToolTip("Pick a filament from filamentDB")

        layout.addWidget(self.slot_name_label)
        layout.addWidget(self.hex_edit, 1)
        layout.addWidget(self.color_button)
        layout.addWidget(self.td_spin)
        layout.addWidget(self.db_button)
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
        self.preview_source_image: Optional[Image.Image] = None
        self.live_nuance_preview_image: Optional[Image.Image] = None
        self.default_profiles = engine.default_material_profiles()
        self.material_rows: Dict[str, MaterialRow] = {}
        self.app_icon_path = RUNTIME_PROJECT_DIR / "leadlight_icon.svg"
        self.filament_db_path = self._load_filament_db_path()
        self._restored_window_state = False

        self.setWindowTitle("LeadLight")
        if self.app_icon_path.exists():
            self.setWindowIcon(QIcon(str(self.app_icon_path)))
        self._build_ui()
        self._restore_ui_state()
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
        saved_geometry = self.settings.value("window_geometry")
        if saved_geometry:
            self.restoreGeometry(saved_geometry)
            saved_splitter = self.settings.value("main_splitter_state")
            if saved_splitter and hasattr(self, "main_splitter"):
                self.main_splitter.restoreState(saved_splitter)
            self._restored_window_state = True
            self._fit_window_to_screen()
            return

        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1120, 620)
            return
        available = screen.availableGeometry()
        width = min(max(640, int(available.width() * 0.90)), available.width())
        height = min(max(420, int(available.height() * 0.90)), available.height())
        self.resize(width, height)
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        QTimer.singleShot(0, self._fit_window_to_screen)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.settings.setValue("window_geometry", self.saveGeometry())
        if hasattr(self, "main_splitter"):
            self.settings.setValue("main_splitter_state", self.main_splitter.saveState())
        super().closeEvent(event)

    def _fit_window_to_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        target_width = min(self.width(), available.width())
        target_height = min(self.height(), available.height())
        if target_width != self.width() or target_height != self.height():
            self.resize(target_width, target_height)
        frame = self.frameGeometry()
        top_left = frame.topLeft()
        max_x = max(available.left(), available.right() - frame.width() + 1)
        max_y = max(available.top(), available.bottom() - frame.height() + 1)
        top_left.setX(min(max(available.left(), top_left.x()), max_x))
        top_left.setY(min(max(available.top(), top_left.y()), max_y))
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
        self.main_splitter = splitter

        preview_panel = self._build_preview_panel()
        controls_panel = self._build_controls_panel()
        right_pane = self._build_right_pane(controls_panel)
        preview_panel.setMinimumHeight(0)
        controls_panel.setMinimumHeight(0)
        right_pane.setMinimumHeight(0)

        splitter.addWidget(preview_panel)
        splitter.addWidget(right_pane)
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([720, 480])

        root_layout.addWidget(splitter, 1)
        footer = QLabel("Dimensions are in millimeters.")
        footer.setStyleSheet("font-size: 11px; color: #8a7763;")
        footer.setAlignment(Qt.AlignRight)
        root_layout.addWidget(footer)
        self.setCentralWidget(root)

    def _wrap_scroll_panel(self, panel: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(panel)
        return scroll

    def _build_right_pane(self, controls_panel: QWidget) -> QWidget:
        panel = QWidget()
        panel.setMinimumHeight(0)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._build_action_bar(), 0)
        layout.addWidget(self._wrap_scroll_panel(controls_panel), 1)
        return panel

    def _panel_state_key(self, name: str) -> str:
        return f"panel_state/{name}"

    def _load_panel_state(self, name: str, default: bool) -> bool:
        raw_value = self.settings.value(self._panel_state_key(name), default)
        if isinstance(raw_value, bool):
            return raw_value
        return str(raw_value).strip().lower() in {"1", "true", "yes"}

    def _save_panel_state(self, name: str, expanded: bool) -> None:
        self.settings.setValue(self._panel_state_key(name), expanded)

    def _build_collapsible_section(self, name: str, title: str, content: QWidget, default_expanded: bool = True) -> CollapsibleSection:
        return CollapsibleSection(
            title,
            content,
            expanded=self._load_panel_state(name, default_expanded),
            on_toggle=lambda expanded, section_name=name: self._save_panel_state(section_name, expanded),
        )

    def _build_controls_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumHeight(0)
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        layout.addWidget(self._build_collapsible_section("source", "Source", self._build_source_group()))
        layout.addWidget(self._build_collapsible_section("model", "Model", self._build_model_group()))
        layout.addWidget(self._build_collapsible_section("materials", "Materials", self._build_materials_group()))
        layout.addWidget(self._build_collapsible_section("status", "Status", self._build_status_group()))
        layout.addWidget(self._build_collapsible_section("run_log", "Run Log", self._build_log_group(), default_expanded=False))
        layout.addStretch(1)
        return panel

    def _build_source_group(self) -> QWidget:
        image_group = QGroupBox("Source")
        image_grid = QGridLayout(image_group)
        image_grid.setContentsMargins(18, 18, 18, 18)
        image_grid.setHorizontalSpacing(12)
        image_grid.setVerticalSpacing(10)
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setPlaceholderText(str(Path.home() / "Desktop" / "image.png"))
        browse_button = QPushButton("Choose Image")
        browse_button.clicked.connect(self.choose_image)
        image_grid.addWidget(QLabel("Image"), 0, 0)
        image_grid.addWidget(self.image_path_edit, 0, 1)
        image_grid.addWidget(browse_button, 0, 2)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional short description")
        image_grid.addWidget(QLabel("Description"), 1, 0)
        image_grid.addWidget(self.description_edit, 1, 1, 1, 2)

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Optional custom output 3MF path")
        output_button = QPushButton("Browse")
        output_button.clicked.connect(self.choose_output)
        image_grid.addWidget(QLabel("Output"), 2, 0)
        image_grid.addWidget(self.output_edit, 2, 1)
        image_grid.addWidget(output_button, 2, 2)
        return image_group

    def _build_model_group(self) -> QWidget:
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
        self.lead_height_spin = self._make_mm_spin(
            0.01,
            10.0,
            max(0.01, engine.DEFAULT_LEAD_CAP_HEIGHT_MM),
            0.05,
        )
        self.lead_thickness_spin = self._make_mm_spin(0.01, 10.0, engine.DEFAULT_LEAD_THICKNESS_MM, 0.05)
        self.lead_mode_combo = QComboBox()
        self.lead_mode_combo.addItems(["generate", "detect"])
        self.seed_spin = QDoubleSpinBox()
        self.seed_spin.setRange(0, 999999)
        self.seed_spin.setDecimals(0)
        self.seed_spin.setValue(7)
        self.seed_spin.setSingleStep(1)

        self.blur_slider, self.blur_value_label = self._make_labeled_slider(
            minimum=1,
            maximum=200,
            value=max(1, int(round(engine.DEFAULT_BLUR_MM * 100))),
            formatter=lambda current: f"{current / 100.0:.2f} mm",
        )
        self.nuances_slider, self.nuances_value_label = self._make_labeled_slider(
            minimum=4,
            maximum=10,
            value=DEFAULT_GUI_NUM_NUANCES,
            formatter=lambda current: f"{current:d}",
        )
        self.saturation_slider, self.saturation_value_label = self._make_labeled_slider(
            minimum=50,
            maximum=200,
            value=int(round(engine.DEFAULT_SATURATION_FACTOR * 100)),
            formatter=lambda current: f"{current / 100.0:.2f}x",
        )
        self.brightness_slider, self.brightness_value_label = self._make_labeled_slider(
            minimum=50,
            maximum=200,
            value=int(round(engine.DEFAULT_BRIGHTNESS_FACTOR * 100)),
            formatter=lambda current: f"{current / 100.0:.2f}x",
        )
        self.blur_slider.valueChanged.connect(self._update_live_preview)
        self.nuances_slider.valueChanged.connect(self._update_live_preview)
        self.saturation_slider.valueChanged.connect(self._update_live_preview)
        self.brightness_slider.valueChanged.connect(self._update_live_preview)

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

        self._add_model_row(settings_grid, 0, "Picture size", size_widget, reset_callback=self._reset_picture_size)
        self._add_model_row(settings_grid, 1, "Plate size", self.plate_size_edit, reset_callback=lambda: self.plate_size_edit.setText("270x270"))
        self._add_model_row(settings_grid, 2, "Resolution", self.resolution_spin, reset_callback=lambda: self.resolution_spin.setValue(engine.DEFAULT_RESOLUTION_MM))
        self._add_model_row(settings_grid, 3, "Layer height", self.layer_height_spin, reset_callback=lambda: self.layer_height_spin.setValue(engine.DEFAULT_BASE_LAYER_HEIGHT_MM))
        self._add_model_row(settings_grid, 4, "Base layers", self.base_layers_spin, reset_callback=lambda: self.base_layers_spin.setValue(engine.DEFAULT_BASE_LAYER_COUNT))
        self._add_model_row(settings_grid, 5, "Lead layer height", self.lead_height_spin, reset_callback=lambda: self.lead_height_spin.setValue(max(0.01, engine.DEFAULT_LEAD_CAP_HEIGHT_MM)))
        self._add_model_row(settings_grid, 6, "Lead", self.lead_mode_combo, reset_callback=lambda: self.lead_mode_combo.setCurrentText("generate"))
        self._add_model_row(settings_grid, 7, "Lead thickness", self.lead_thickness_spin, reset_callback=lambda: self.lead_thickness_spin.setValue(engine.DEFAULT_LEAD_THICKNESS_MM))
        self._add_model_row(settings_grid, 8, "Blur", self.blur_slider, self.blur_value_label, reset_callback=lambda: self.blur_slider.setValue(max(1, int(round(engine.DEFAULT_BLUR_MM * 100)))))
        self._add_model_row(settings_grid, 9, "Nuances", self.nuances_slider, self.nuances_value_label, reset_callback=lambda: self.nuances_slider.setValue(DEFAULT_GUI_NUM_NUANCES))
        self._add_model_row(settings_grid, 10, "Saturation", self.saturation_slider, self.saturation_value_label, reset_callback=lambda: self.saturation_slider.setValue(int(round(engine.DEFAULT_SATURATION_FACTOR * 100))))
        self._add_model_row(settings_grid, 11, "Brightness", self.brightness_slider, self.brightness_value_label, reset_callback=lambda: self.brightness_slider.setValue(int(round(engine.DEFAULT_BRIGHTNESS_FACTOR * 100))))
        self._add_model_row(settings_grid, 12, "Seed", self.seed_spin, reset_callback=lambda: self.seed_spin.setValue(7))
        return settings_group

    def _add_model_row(
        self,
        grid: QGridLayout,
        row: int,
        label: str,
        control: QWidget,
        value_widget: Optional[QWidget] = None,
        *,
        reset_callback,
    ) -> None:
        grid.addWidget(QLabel(label), row, 0)
        grid.addWidget(control, row, 1)
        if value_widget is not None:
            grid.addWidget(value_widget, row, 2)
        reset_button = self._make_reset_button(reset_callback)
        grid.addWidget(reset_button, row, 3)

    def _make_reset_button(self, callback) -> QPushButton:
        button = QPushButton("↺")
        button.setFixedWidth(34)
        button.setToolTip("Reset to default")
        button.clicked.connect(callback)
        return button

    def _reset_picture_size(self) -> None:
        self.size_slider.setValue(int(DEFAULT_LONG_SIDE_MM))
        if self.input_path is not None:
            self._sync_size_from_image(self.input_path)
        else:
            self.size_edit.clear()
            self.size_slider_label.setText("Long side: auto")

    def _build_action_bar(self) -> QWidget:
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
        return run_buttons

    def _setting_key(self, name: str) -> str:
        return f"ui/{name}"

    def _restore_ui_state(self) -> None:
        self.image_path_edit.setText(str(self.settings.value(self._setting_key("image_path"), "")))
        self.description_edit.setText(str(self.settings.value(self._setting_key("description"), "")))
        self.output_edit.setText(str(self.settings.value(self._setting_key("output_path"), "")))
        self.plate_size_edit.setText(str(self.settings.value(self._setting_key("plate_size"), "270x270")))
        self.size_edit.setText(str(self.settings.value(self._setting_key("size_text"), "")))
        self.resolution_spin.setValue(float(self.settings.value(self._setting_key("resolution"), engine.DEFAULT_RESOLUTION_MM)))
        self.layer_height_spin.setValue(float(self.settings.value(self._setting_key("layer_height"), engine.DEFAULT_BASE_LAYER_HEIGHT_MM)))
        self.base_layers_spin.setValue(float(self.settings.value(self._setting_key("base_layers"), engine.DEFAULT_BASE_LAYER_COUNT)))
        self.lead_height_spin.setValue(float(self.settings.value(self._setting_key("lead_height"), max(0.01, engine.DEFAULT_LEAD_CAP_HEIGHT_MM))))
        self.lead_mode_combo.setCurrentText(str(self.settings.value(self._setting_key("lead_mode"), "generate")))
        self.lead_thickness_spin.setValue(float(self.settings.value(self._setting_key("lead_thickness"), engine.DEFAULT_LEAD_THICKNESS_MM)))
        self.blur_slider.setValue(int(self.settings.value(self._setting_key("blur_slider"), max(1, int(round(engine.DEFAULT_BLUR_MM * 100))))))
        self.nuances_slider.setValue(int(self.settings.value(self._setting_key("nuances_slider"), DEFAULT_GUI_NUM_NUANCES)))
        self.saturation_slider.setValue(int(self.settings.value(self._setting_key("saturation_slider"), int(round(engine.DEFAULT_SATURATION_FACTOR * 100)))))
        self.brightness_slider.setValue(int(self.settings.value(self._setting_key("brightness_slider"), int(round(engine.DEFAULT_BRIGHTNESS_FACTOR * 100)))))
        self.seed_spin.setValue(float(self.settings.value(self._setting_key("seed"), 7)))
        self._connect_ui_state_persistence()

        image_path = self._effective_image_path()
        if image_path is not None and image_path.exists():
            self.input_path = image_path
            self._load_preview_source_image(image_path)
            self._sync_size_from_image(image_path)
            saved_size_slider = self.settings.value(self._setting_key("size_slider"))
            if saved_size_slider is not None:
                self.size_slider.setValue(int(saved_size_slider))
            saved_size_text = str(self.settings.value(self._setting_key("size_text"), "")).strip()
            if saved_size_text:
                self.size_edit.setText(saved_size_text)
            self._update_live_preview()
            self._set_stage_index(0)
        else:
            self._update_live_preview()

    def _connect_ui_state_persistence(self) -> None:
        self.image_path_edit.textChanged.connect(lambda value: self.settings.setValue(self._setting_key("image_path"), value))
        self.description_edit.textChanged.connect(lambda value: self.settings.setValue(self._setting_key("description"), value))
        self.output_edit.textChanged.connect(lambda value: self.settings.setValue(self._setting_key("output_path"), value))
        self.size_edit.textChanged.connect(lambda value: self.settings.setValue(self._setting_key("size_text"), value))
        self.plate_size_edit.textChanged.connect(lambda value: self.settings.setValue(self._setting_key("plate_size"), value))
        self.size_slider.valueChanged.connect(lambda value: self.settings.setValue(self._setting_key("size_slider"), value))
        self.resolution_spin.valueChanged.connect(lambda value: self.settings.setValue(self._setting_key("resolution"), value))
        self.layer_height_spin.valueChanged.connect(lambda value: self.settings.setValue(self._setting_key("layer_height"), value))
        self.base_layers_spin.valueChanged.connect(lambda value: self.settings.setValue(self._setting_key("base_layers"), value))
        self.lead_height_spin.valueChanged.connect(lambda value: self.settings.setValue(self._setting_key("lead_height"), value))
        self.lead_mode_combo.currentTextChanged.connect(lambda value: self.settings.setValue(self._setting_key("lead_mode"), value))
        self.lead_thickness_spin.valueChanged.connect(lambda value: self.settings.setValue(self._setting_key("lead_thickness"), value))
        self.blur_slider.valueChanged.connect(lambda value: self.settings.setValue(self._setting_key("blur_slider"), value))
        self.nuances_slider.valueChanged.connect(lambda value: self.settings.setValue(self._setting_key("nuances_slider"), value))
        self.saturation_slider.valueChanged.connect(lambda value: self.settings.setValue(self._setting_key("saturation_slider"), value))
        self.brightness_slider.valueChanged.connect(lambda value: self.settings.setValue(self._setting_key("brightness_slider"), value))
        self.seed_spin.valueChanged.connect(lambda value: self.settings.setValue(self._setting_key("seed"), value))

    def _build_preview_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumHeight(0)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        preview_group = QGroupBox("")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(18, 18, 18, 18)
        preview_layout.setSpacing(10)

        preview_header = QWidget()
        preview_header_layout = QHBoxLayout(preview_header)
        preview_header_layout.setContentsMargins(0, 0, 0, 0)
        preview_header_layout.setSpacing(8)
        preview_title = QLabel("Preview:")
        preview_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #584635;")
        self.preview_step_label = QLabel("No image")
        self.preview_step_label.setStyleSheet("font-size: 15px; color: #715d49;")
        preview_header_layout.addWidget(preview_title)
        preview_header_layout.addWidget(self.preview_step_label, 1)

        self.preview_step_slider = QSlider(Qt.Horizontal)
        self.preview_step_slider.setRange(0, 0)
        self.preview_step_slider.setSingleStep(1)
        self.preview_step_slider.setPageStep(1)
        self.preview_step_slider.setEnabled(False)
        self.preview_step_slider.valueChanged.connect(self._set_stage_index)

        self.preview_display = ImagePreview("Preview will appear here")

        preview_layout.addWidget(preview_header)
        preview_layout.addWidget(self.preview_step_slider)
        preview_layout.addWidget(self.preview_display, 1)

        layout.addWidget(preview_group, 1)
        self._update_preview_slider()
        return panel

    def _build_materials_group(self) -> QWidget:
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
        return materials_group

    def _build_status_group(self) -> QWidget:
        summary_group = QGroupBox("Status")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setContentsMargins(18, 18, 18, 18)
        self.summary_label = QLabel("Choose an image and generate a 3MF.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setObjectName("statusBanner")
        summary_layout.addWidget(self.summary_label)
        return summary_group

    def _build_log_group(self) -> QWidget:
        log_group = QGroupBox("Run Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(18, 18, 18, 18)
        self.log_view = NaturalScrollTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(80)
        log_layout.addWidget(self.log_view)
        return log_group

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
                selection-background-color: #c7d9e8;
                selection-color: #2f241a;
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

    def _make_labeled_slider(
        self,
        *,
        minimum: int,
        maximum: int,
        value: int,
        formatter,
    ) -> tuple[QSlider, QLabel]:
        slider = QSlider(Qt.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        label = QLabel(formatter(value))
        label.setMinimumWidth(72)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet("color: #715d49; font-size: 12px;")
        slider.valueChanged.connect(lambda current: label.setText(formatter(current)))
        return slider, label

    def _current_blur_mm(self) -> float:
        return max(0.01, self.blur_slider.value() / 100.0)

    def _current_saturation(self) -> float:
        return self.saturation_slider.value() / 100.0

    def _current_brightness(self) -> float:
        return self.brightness_slider.value() / 100.0

    def _current_num_nuances(self) -> int:
        return int(self.nuances_slider.value())

    def _prepare_dialog(self) -> None:
        self.raise_()
        self.activateWindow()

    def _load_preview_source_image(self, image_path: Path) -> None:
        with Image.open(image_path) as source_image:
            preview_image = source_image.convert("RGB")
            preview_image.thumbnail((PREVIEW_RENDER_MAX_SIDE_PX, PREVIEW_RENDER_MAX_SIDE_PX), Image.Resampling.LANCZOS)
        self.preview_source_image = preview_image.copy()

    def _build_preprocessed_preview_image(self) -> Optional[Image.Image]:
        if self.preview_source_image is None:
            return None
        preview_image = self.preview_source_image.copy()
        saturation = self._current_saturation()
        brightness = self._current_brightness()
        blur_mm = self._current_blur_mm()
        if abs(saturation - 1.0) > 1e-9:
            preview_image = ImageEnhance.Color(preview_image).enhance(saturation)
        if abs(brightness - 1.0) > 1e-9:
            preview_image = ImageEnhance.Brightness(preview_image).enhance(brightness)
        if blur_mm > 0:
            preview_image = preview_image.filter(ImageFilter.GaussianBlur(radius=blur_mm * 1.5))
        return preview_image

    def _build_live_preview_image(self) -> Optional[Image.Image]:
        preview_image = self._build_preprocessed_preview_image()
        if preview_image is None:
            return None
        rgb_array = np.asarray(preview_image, dtype=np.uint8)
        flat_rgb = rgb_array.reshape(-1, 3)
        flat_lab = engine.srgb_to_lab(rgb_array).reshape(-1, 3).astype(np.float32)
        raw_labels, lab_centers = engine.kmeans(flat_lab, clusters=self._current_num_nuances(), seed=int(self.seed_spin.value()))
        labels, _sorted_lab, region_colors = engine.reorder_by_lightness(raw_labels, lab_centers, flat_rgb)
        labels = labels.reshape(rgb_array.shape[0], rgb_array.shape[1])
        labels = engine.majority_smooth(labels, num_classes=self._current_num_nuances(), passes=2)
        return engine.build_preview(labels, region_colors, np.zeros_like(labels, dtype=bool))

    def _update_live_preview(self) -> None:
        self.live_nuance_preview_image = self._build_live_preview_image()
        self._update_preview_slider()
        if self.stage_index in (0, 1):
            self._set_stage_index(self.stage_index if self.stage_index >= 0 else 0)

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
        self._load_preview_source_image(self.input_path)
        self._update_live_preview()
        self._set_stage_index(0)
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
        self._load_preview_source_image(image_path)
        self._update_live_preview()
        self.preview_path = None
        self.output_path = None
        self.stage_paths = []
        self.stage_index = 0
        self.stage_dir = Path(tempfile.mkdtemp(prefix="leadlight_stages_"))
        self._update_preview_slider()
        self._set_stage_index(0)

        script_args = [
            str(image_path),
            "--num-nuances",
            str(self._current_num_nuances()),
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
            f"{self._current_blur_mm():.2f}",
            "--saturation",
            f"{self._current_saturation():.2f}",
            "--brightness",
            f"{self._current_brightness():.2f}",
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
            if self.stage_paths:
                self._set_stage_index(len(self.stage_paths))
        else:
            self.summary_label.setText("Generation failed. See the run log for details.")
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
            self._update_preview_slider()
            self._set_stage_index(len(self.stage_paths))

    def _set_stage_index(self, index: int) -> None:
        total_steps = self._preview_step_count()
        if total_steps == 0:
            self.stage_index = -1
            self.preview_display.set_image(None, "Preview will appear here")
            self.preview_step_slider.setToolTip("No preview loaded yet")
            self.preview_step_label.setText("No image")
            return
        self.stage_index = max(0, min(index, total_steps - 1))
        self.preview_step_slider.blockSignals(True)
        self.preview_step_slider.setValue(self.stage_index)
        self.preview_step_slider.blockSignals(False)
        if self.stage_index == 0:
            self.preview_display.set_pil_image(self._build_preprocessed_preview_image(), "Preview will appear here")
            self.preview_step_slider.setToolTip("Step 0: source preview")
            self.preview_step_label.setText("Original")
            return

        if self.live_nuance_preview_image is not None and self.stage_index == 1:
            self.preview_display.set_pil_image(self.live_nuance_preview_image, "Preview will appear here")
            self.preview_step_slider.setToolTip("Step 1: live nuance preview")
            self.preview_step_label.setText("Live Nuance")
            return

        stage_offset = 1 if self.live_nuance_preview_image is not None else 0
        name, path = self.stage_paths[self.stage_index - 1 - stage_offset]
        self.preview_display.set_image(path, "Preview will appear here")
        self.preview_step_slider.setToolTip(f"Step {self.stage_index}: {name.replace('_', ' ')}")
        self.preview_step_label.setText(name.replace("_", " ").title())

    def _preview_step_count(self) -> int:
        if self.preview_source_image is None:
            return 0
        return 1 + (1 if self.live_nuance_preview_image is not None else 0) + len(self.stage_paths)

    def _update_preview_slider(self) -> None:
        total_steps = self._preview_step_count()
        maximum = max(0, total_steps - 1)
        current_index = self.stage_index if self.stage_index >= 0 else 0
        self.preview_step_slider.blockSignals(True)
        self.preview_step_slider.setRange(0, maximum)
        self.preview_step_slider.setEnabled(total_steps > 0)
        self.preview_step_slider.setValue(min(current_index, maximum))
        self.preview_step_slider.blockSignals(False)

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
