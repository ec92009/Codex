#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt, QProcess, QSize, QTimer
from PySide6.QtGui import QColor, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
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
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
)

import image_grade_to_3mf as engine


PROJECT_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = PROJECT_DIR / "image_grade_to_3mf.py"
PRESET_PATH = PROJECT_DIR / "material_presets.json"


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

        layout.addWidget(self.slot_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.hex_edit)
        layout.addWidget(self.color_button)
        layout.addWidget(self.td_spin)
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.process: Optional[QProcess] = None
        self.input_path: Optional[Path] = None
        self.preview_path: Optional[Path] = None
        self.output_path: Optional[Path] = None
        self.default_profiles = engine.default_material_profiles()
        self.material_rows: Dict[str, MaterialRow] = {}

        self.setWindowTitle("Image to 3MF Studio")
        self._build_ui()
        self._apply_style()
        self.reset_materials()
        self._apply_initial_geometry()

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

        header = QLabel("Image to 3MF Studio")
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
        self.setCentralWidget(root)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        image_group = QGroupBox("Source")
        image_form = QFormLayout(image_group)
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
        settings_grid.setHorizontalSpacing(10)
        settings_grid.setVerticalSpacing(8)

        self.size_edit = QLineEdit("100x100")
        self.plate_size_edit = QLineEdit("270x270")
        self.resolution_spin = self._make_mm_spin(0.01, 5.0, engine.DEFAULT_RESOLUTION_MM, 0.05)
        self.layer_height_spin = self._make_mm_spin(0.01, 5.0, engine.DEFAULT_BASE_LAYER_HEIGHT_MM, 0.05)
        self.base_layers_spin = QDoubleSpinBox()
        self.base_layers_spin.setRange(1, 99)
        self.base_layers_spin.setDecimals(0)
        self.base_layers_spin.setValue(engine.DEFAULT_BASE_LAYER_COUNT)
        self.base_layers_spin.setSingleStep(1)
        self.lead_height_spin = self._make_mm_spin(0.0, 10.0, engine.DEFAULT_LEAD_CAP_HEIGHT_MM, 0.05)
        self.lead_thickness_spin = self._make_mm_spin(0.01, 10.0, engine.DEFAULT_LEAD_THICKNESS_MM, 0.05)
        self.seed_spin = QDoubleSpinBox()
        self.seed_spin.setRange(0, 999999)
        self.seed_spin.setDecimals(0)
        self.seed_spin.setValue(7)
        self.seed_spin.setSingleStep(1)

        self.blur_combo = QComboBox()
        self.blur_combo.addItems(["none", "low", "medium", "strong"])

        settings_grid.addWidget(QLabel("Picture size"), 0, 0)
        settings_grid.addWidget(self.size_edit, 0, 1)
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
        settings_grid.addWidget(QLabel("Lead thickness"), 6, 0)
        settings_grid.addWidget(self.lead_thickness_spin, 6, 1)
        settings_grid.addWidget(QLabel("Blur"), 7, 0)
        settings_grid.addWidget(self.blur_combo, 7, 1)
        settings_grid.addWidget(QLabel("Seed"), 8, 0)
        settings_grid.addWidget(self.seed_spin, 8, 1)

        self.open_orca_checkbox = QCheckBox("Open result in Snapmaker Orca")
        self.open_orca_checkbox.setChecked(True)
        settings_grid.addWidget(self.open_orca_checkbox, 9, 0, 1, 2)

        layout.addWidget(settings_group)

        run_buttons = QWidget()
        run_buttons_layout = QHBoxLayout(run_buttons)
        run_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.generate_button = QPushButton("Generate 3MF")
        self.generate_button.clicked.connect(self.run_export)
        self.generate_button.setMinimumHeight(40)
        reveal_button = QPushButton("Reveal Output")
        reveal_button.clicked.connect(self.reveal_output)
        run_buttons_layout.addWidget(self.generate_button, 1)
        run_buttons_layout.addWidget(reveal_button)
        layout.addWidget(run_buttons)

        layout.addStretch(1)
        return panel

    def _build_preview_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        self.original_preview = ImagePreview("Original image preview")
        self.generated_preview = ImagePreview("Generated preview will appear here")

        original_group = QGroupBox("Original")
        original_layout = QVBoxLayout(original_group)
        original_layout.addWidget(self.original_preview)

        summary_group = QGroupBox("Status")
        summary_layout = QVBoxLayout(summary_group)
        self.summary_label = QLabel("Choose an image and generate a 3MF.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("color: #5e4b39;")
        summary_layout.addWidget(self.summary_label)

        generated_group = QGroupBox("Generated Preview")
        generated_layout = QVBoxLayout(generated_group)
        generated_layout.addWidget(self.generated_preview)

        progress_group = QGroupBox("Export Status")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_label = QLabel("Idle")
        self.progress_label.setStyleSheet("color: #715d49; font-weight: 600;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(original_group, 1)
        layout.addWidget(summary_group, 0)
        layout.addWidget(progress_group, 0)
        layout.addWidget(generated_group, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        materials_group = QGroupBox("Materials")
        materials_layout = QVBoxLayout(materials_group)
        materials_layout.setSpacing(8)
        materials_help = QLabel("Use measured TD values when you have them. Leave untouched to use the built-in CMYWK defaults.")
        materials_help.setWordWrap(True)
        materials_help.setStyleSheet("color: #715d49;")
        materials_layout.addWidget(materials_help)

        for slot in ("1", "2", "3", "4", "5"):
            row = MaterialRow(slot, self.default_profiles[slot])
            self.material_rows[slot] = row
            materials_layout.addWidget(row)

        materials_buttons = QWidget()
        materials_buttons_layout = QHBoxLayout(materials_buttons)
        materials_buttons_layout.setContentsMargins(0, 0, 0, 0)
        reset_button = QPushButton("Reset CMYWK")
        reset_button.clicked.connect(self.reset_materials)
        save_button = QPushButton("Save Preset")
        save_button.clicked.connect(self.save_preset)
        load_button = QPushButton("Load Preset")
        load_button.clicked.connect(self.load_preset)
        materials_buttons_layout.addWidget(reset_button)
        materials_buttons_layout.addWidget(save_button)
        materials_buttons_layout.addWidget(load_button)
        materials_buttons_layout.addStretch(1)
        materials_layout.addWidget(materials_buttons)

        log_group = QGroupBox("Run Log")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)

        layout.addWidget(materials_group, 0)
        layout.addWidget(log_group, 1)
        return panel

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
            QLineEdit, QTextEdit, QComboBox, QDoubleSpinBox {
                background: #fffdfa;
                border: 1px solid #cfbfa7;
                border-radius: 8px;
                padding: 6px 8px;
            }
            QProgressBar {
                background: #eadbc8;
                border: 1px solid #cfbfa7;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background: #b56f38;
                border-radius: 4px;
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
            QPushButton:disabled {
                background: #c6b7a6;
                color: #f1ece6;
            }
            QCheckBox {
                spacing: 8px;
            }
            """
        )

    def _make_mm_spin(self, minimum: float, maximum: float, value: float, step: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(2)
        spin.setValue(value)
        spin.setSingleStep(step)
        spin.setSuffix(" mm")
        return spin

    def _dialog_options(self) -> QFileDialog.Option:
        options = QFileDialog.Option(0)
        if sys.platform == "darwin":
            options |= QFileDialog.Option.DontUseNativeDialog
        return options

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
            options=self._dialog_options(),
        )
        if not path:
            return
        self.input_path = Path(path)
        self.image_path_edit.setText(path)
        self.original_preview.set_image(self.input_path, "Original image preview")

    def choose_output(self) -> None:
        self._prepare_dialog()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose output 3MF path",
            str(PROJECT_DIR / "out" / "output.3mf"),
            "3MF Files (*.3mf)",
            options=self._dialog_options(),
        )
        if path:
            self.output_edit.setText(path)

    def reset_materials(self) -> None:
        for slot, row in self.material_rows.items():
            row.set_profile(self.default_profiles[slot])

    def save_preset(self) -> None:
        self._prepare_dialog()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save material preset",
            str(PRESET_PATH),
            "JSON Files (*.json)",
            options=self._dialog_options(),
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
            str(PRESET_PATH if PRESET_PATH.exists() else PROJECT_DIR),
            "JSON Files (*.json)",
            options=self._dialog_options(),
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

    def run_export(self) -> None:
        image_path = self._effective_image_path()
        if image_path is None:
            QMessageBox.information(self, "Image required", "Choose an image before generating a 3MF.")
            return
        if not image_path.exists():
            QMessageBox.warning(self, "Missing image", f"Image not found:\n{image_path}")
            return

        self.input_path = image_path
        self.original_preview.set_image(image_path, "Original image preview")
        self.generated_preview.set_image(None, "Generated preview will appear here")
        self.preview_path = None
        self.output_path = None

        args = [
            str(SCRIPT_PATH),
            str(image_path),
            "--size",
            self.size_edit.text().strip() or "100x100",
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
            "--lead-thickness",
            f"{self.lead_thickness_spin.value():.2f}mm",
            "--blur",
            self.blur_combo.currentText(),
            "--seed",
            str(int(self.seed_spin.value())),
        ]

        description = self.description_edit.text().strip()
        if description:
            args.extend(["--description", description])

        output_path = self.output_edit.text().strip()
        if output_path:
            args.extend(["--output", output_path])

        if not self.open_orca_checkbox.isChecked():
            args.append("--no-open")

        args.extend(self._material_args())

        self.log_view.clear()
        self.summary_label.setText("Generating 3MF...")
        self.progress_label.setText("Generating 3MF...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.generate_button.setEnabled(False)

        process = QProcess(self)
        process.setProgram(sys.executable)
        process.setArguments(args)
        process.setWorkingDirectory(str(PROJECT_DIR))
        process.setProcessChannelMode(QProcess.MergedChannels)
        process.readyReadStandardOutput.connect(self._append_process_output)
        process.finished.connect(self._process_finished)
        self.process = process
        process.start()

    def _append_process_output(self) -> None:
        if self.process is None:
            return
        chunk = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if not chunk:
            return
        self.log_view.moveCursor(QTextCursor.End)
        self.log_view.insertPlainText(chunk)
        self.log_view.moveCursor(QTextCursor.End)

    def _process_finished(self, exit_code: int, _status) -> None:
        self.generate_button.setEnabled(True)
        log_text = self.log_view.toPlainText()
        self.preview_path = self._extract_path(log_text, "Preview PNG:")
        self.output_path = self._extract_path(log_text, "3MF output:")
        self.generated_preview.set_image(self.preview_path, "Generated preview will appear here")

        if exit_code == 0:
            summary = "3MF generated successfully."
            if self.output_path is not None:
                summary += f"\nOutput: {self.output_path}"
            if self.preview_path is not None:
                summary += f"\nPreview: {self.preview_path}"
            self.summary_label.setText(summary)
            self.progress_label.setText("Done")
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)
        else:
            self.summary_label.setText("Generation failed. See the run log for details.")
            self.progress_label.setText("Failed")
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)
            QMessageBox.warning(self, "Generation failed", "The export did not complete successfully. See the run log.")
        self.process = None

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


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
