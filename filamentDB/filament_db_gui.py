#!/usr/bin/env python3

from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QColorDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from filament_db import (
    DEFAULT_DB_PATH,
    add_filament,
    connect,
    detect_td1_device,
    ensure_hex_color,
    migrate_schema,
    read_td1_scan,
    update_filament_color,
)


class ScanWorker(QThread):
    finished_scan = Signal(float, str, str)
    failed_scan = Signal(str)

    def __init__(self, device_path: Path, timeout: float) -> None:
        super().__init__()
        self.device_path = device_path
        self.timeout = timeout

    def run(self) -> None:
        try:
            td, color = read_td1_scan(self.device_path, self.timeout)
        except Exception as exc:  # pragma: no cover - UI error path
            self.failed_scan.emit(str(exc))
            return
        self.finished_scan.emit(td, color, str(self.device_path))


class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, numeric_value: float | int, text: str) -> None:
        super().__init__(text)
        self.numeric_value = numeric_value

    def __lt__(self, other: object) -> bool:
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_value < other.numeric_value
        return super().__lt__(other)


class FilamentDbWindow(QMainWindow):
    COLOR_SWATCH_COLUMN = 4

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("filamentDB")
        self.resize(980, 640)

        self.db_path = DEFAULT_DB_PATH
        self.connection = connect(self.db_path)
        migrate_schema(self.connection)
        self.scan_worker: ScanWorker | None = None
        self.last_saved_record_id: int | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        left_column = QVBoxLayout()
        left_column.setSpacing(16)
        root.addLayout(left_column, 0)

        right_column = QVBoxLayout()
        right_column.setSpacing(16)
        root.addLayout(right_column, 1)

        left_column.addWidget(self._build_scan_panel())
        left_column.addWidget(self._build_details_panel())
        left_column.addStretch(1)

        right_column.addWidget(self._build_table_panel(), 1)

        status = QStatusBar()
        status.showMessage(f"Database: {self.db_path}")
        self.setStatusBar(status)

        self.refresh_choices()
        self.refresh_table()

    def _build_scan_panel(self) -> QGroupBox:
        box = QGroupBox("Scan")
        layout = QVBoxLayout(box)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self.brand_combo = self._editable_combo("SUNLU")
        self.type_combo = self._editable_combo("PLA+ 2.0")
        self.name_combo = self._editable_combo("Coffee")
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Optional notes")

        form.addRow("Brand", self.brand_combo)
        form.addRow("Type", self.type_combo)
        form.addRow("Name", self.name_combo)
        form.addRow("Notes", self.notes_input)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.scan_button = QPushButton("Scan from TD1")
        self.scan_button.clicked.connect(self.start_scan)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all)

        button_row.addWidget(self.scan_button)
        button_row.addWidget(self.refresh_button)
        layout.addLayout(button_row)

        self.scan_status = QLabel("Ready. Put filament in the TD1 and press Scan from TD1.")
        self.scan_status.setWordWrap(True)
        layout.addWidget(self.scan_status)

        return box

    def _build_details_panel(self) -> QGroupBox:
        box = QGroupBox("Last Scan")
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.device_value = QLabel("Auto-detect")
        self.td_value = QLabel("—")
        self.hex_input = QLineEdit()
        self.hex_input.setPlaceholderText("#AABBCC")
        self.hex_input.setMaximumWidth(120)
        self.hex_input.textChanged.connect(self.on_hex_changed)
        self.color_swatch = QLabel()
        self.color_swatch.setFixedSize(28, 28)
        self.color_swatch.setStyleSheet("border: 1px solid #888; border-radius: 4px; background: #cccccc;")
        self.pick_color_button = QPushButton("Pick")
        self.pick_color_button.clicked.connect(self.pick_color)
        self.save_color_button = QPushButton("Save Color")
        self.save_color_button.clicked.connect(self.save_manual_color)
        self.save_color_button.setEnabled(False)
        self.saved_value = QLabel("—")

        hex_row = QHBoxLayout()
        hex_row.setSpacing(8)
        hex_row.addWidget(self.hex_input)
        hex_row.addWidget(self.color_swatch)
        hex_row.addWidget(self.pick_color_button)
        hex_row.addWidget(self.save_color_button)
        hex_row.addStretch(1)

        form.addRow("Device", self.device_value)
        form.addRow("TD", self.td_value)
        form.addRow("HEX", hex_row)
        form.addRow("Saved", self.saved_value)
        return box

    def _build_table_panel(self) -> QGroupBox:
        box = QGroupBox("Filaments")
        layout = QVBoxLayout(box)
        layout.setSpacing(10)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self.delete_selected_row)
        controls.addWidget(self.delete_button)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["ID", "Brand", "Type", "Name", "Color", "HEX", "TD", "Source"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(self.on_table_cell_double_clicked)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)
        return box

    @staticmethod
    def _editable_combo(placeholder: str) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.lineEdit().setPlaceholderText(placeholder)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setMinimumWidth(220)
        return combo

    def refresh_all(self) -> None:
        self.refresh_choices()
        self.refresh_table()

    def refresh_choices(self) -> None:
        current_brand = self.brand_combo.currentText()
        current_type = self.type_combo.currentText()
        current_name = self.name_combo.currentText()

        brands = self._fetch_distinct("brand")
        types = self._fetch_distinct("filament_type")
        names = self._fetch_distinct("name")

        self._set_combo_items(self.brand_combo, brands, current_brand)
        self._set_combo_items(self.type_combo, types, current_type)
        self._set_combo_items(self.name_combo, names, current_name)

    def refresh_table(self) -> None:
        rows = list(
            self.connection.execute(
                """
                SELECT id, brand, filament_type, name, color, td, source
                FROM filaments
                ORDER BY id DESC
                LIMIT 200
                """
            )
        )
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
                "" if row["td"] is None else f"{float(row['td']):.2f}",
                row["source"],
            ]
            for column, value in enumerate(values):
                if column == 0:
                    item = NumericTableWidgetItem(int(row["id"]), value)
                elif column == 6:
                    numeric_td = float(row["td"]) if row["td"] is not None else -1.0
                    item = NumericTableWidgetItem(numeric_td, value)
                else:
                    item = QTableWidgetItem(value)
                if column in (0, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == self.COLOR_SWATCH_COLUMN:
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    item.setBackground(QColor(row["color"]))
                    item.setToolTip(f"Double-click to change {row['name']} color")
                self.table.setItem(row_index, column, item)
        self.table.resizeRowsToContents()
        self.table.setSortingEnabled(True)

    def _fetch_distinct(self, column: str) -> list[str]:
        sql = f"SELECT DISTINCT {column} FROM filaments WHERE {column} <> '' ORDER BY {column}"
        return [row[0] for row in self.connection.execute(sql)]

    @staticmethod
    def _set_combo_items(combo: QComboBox, items: list[str], current_text: str) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(items)
        combo.setCurrentText(current_text)
        combo.blockSignals(False)

    def start_scan(self) -> None:
        brand = self.brand_combo.currentText().strip()
        filament_type = self.type_combo.currentText().strip()
        name = self.name_combo.currentText().strip()
        notes = self.notes_input.text().strip()
        if not brand or not filament_type or not name:
            QMessageBox.warning(self, "Missing details", "Please fill in brand, type, and name before scanning.")
            return

        device_path = detect_td1_device()
        if device_path is None:
            QMessageBox.warning(self, "TD1 not found", "No TD1 serial device was found under /dev/cu.usbmodem*.")
            return

        self.scan_button.setEnabled(False)
        self.scan_status.setText("Listening for TD1 scan data...")
        self.device_value.setText(str(device_path))
        self.saved_value.setText("—")
        self.save_color_button.setEnabled(False)

        self.scan_worker = ScanWorker(device_path, timeout=20.0)
        self.scan_worker.finished_scan.connect(lambda td, color, device: self.finish_scan(td, color, device, brand, filament_type, name, notes))
        self.scan_worker.failed_scan.connect(self.fail_scan)
        self.scan_worker.start()

    def finish_scan(
        self,
        td: float,
        color: str,
        device_path: str,
        brand: str,
        filament_type: str,
        name: str,
        notes: str,
    ) -> None:
        record_id = add_filament(
            self.connection,
            brand=brand,
            filament_type=filament_type,
            name=name,
            color=color,
            td=td,
            source="td1",
            notes=notes,
        )
        self.last_saved_record_id = record_id
        self.td_value.setText(f"{td:.2f}")
        self.hex_input.setText(color)
        self._set_swatch_color(color)
        self.device_value.setText(device_path)
        self.saved_value.setText(f"Saved as #{record_id}")
        self.scan_status.setText(f"Saved {brand} {filament_type} {name} with TD {td:.2f} and HEX {color}.")
        self.scan_button.setEnabled(True)
        self.save_color_button.setEnabled(True)
        self.refresh_all()

    def fail_scan(self, error_message: str) -> None:
        self.scan_button.setEnabled(True)
        self.scan_status.setText(f"Scan failed: {error_message}")
        QMessageBox.warning(self, "Scan failed", error_message)

    def on_hex_changed(self, text: str) -> None:
        self._set_swatch_color(text)
        self.save_color_button.setEnabled(self.last_saved_record_id is not None and bool(text.strip()))

    def pick_color(self) -> None:
        current = QColor(self.hex_input.text().strip())
        if not current.isValid():
            current = QColor("#CCCCCC")
        dialog = QColorDialog(current, self)
        dialog.setWindowTitle("Choose Filament Color")
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, False)
        if dialog.exec() != QColorDialog.DialogCode.Accepted:
            return
        chosen = dialog.currentColor()
        if chosen.isValid():
            self.hex_input.setText(chosen.name().upper())

    def save_manual_color(self) -> None:
        if self.last_saved_record_id is None:
            QMessageBox.warning(self, "No scan yet", "Scan and save a filament first, then you can correct its color.")
            return
        try:
            color = ensure_hex_color(self.hex_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid HEX", str(exc))
            return
        updated = update_filament_color(self.connection, self.last_saved_record_id, color)
        if not updated:
            QMessageBox.warning(self, "Update failed", "Could not update the saved filament color.")
            return
        self.hex_input.setText(color)
        self.saved_value.setText(f"Saved as #{self.last_saved_record_id} (color updated)")
        self.scan_status.setText(f"Updated filament #{self.last_saved_record_id} color to {color}.")
        self.refresh_table()

    def _set_swatch_color(self, value: str) -> None:
        color = QColor(value.strip())
        hex_value = color.name().upper() if color.isValid() else "#CCCCCC"
        self.color_swatch.setStyleSheet(
            f"border: 1px solid #888; border-radius: 4px; background: {hex_value};"
        )

    def delete_selected_row(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Nothing selected", "Select a filament row first.")
            return
        row_index = selected_rows[0].row()
        record_id = int(self.table.item(row_index, 0).text())
        name = self.table.item(row_index, 3).text()
        answer = QMessageBox.question(
            self,
            "Delete filament",
            f"Delete filament #{record_id} ({name}) from the database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.connection.execute("DELETE FROM filaments WHERE id = ?", (record_id,))
        self.connection.commit()
        if self.last_saved_record_id == record_id:
            self.last_saved_record_id = None
            self.saved_value.setText("Deleted")
            self.save_color_button.setEnabled(False)
        self.scan_status.setText(f"Deleted filament #{record_id}.")
        self.refresh_all()

    def on_table_cell_double_clicked(self, row: int, column: int) -> None:
        if column != self.COLOR_SWATCH_COLUMN:
            return
        record_id = int(self.table.item(row, 0).text())
        current_hex = self.table.item(row, 5).text()
        current = QColor(current_hex)
        if not current.isValid():
            current = QColor("#CCCCCC")
        dialog = QColorDialog(current, self)
        dialog.setWindowTitle("Choose Filament Color")
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, False)
        if dialog.exec() != QColorDialog.DialogCode.Accepted:
            return
        chosen = dialog.currentColor()
        if not chosen.isValid():
            return
        color = chosen.name().upper()
        if not update_filament_color(self.connection, record_id, color):
            QMessageBox.warning(self, "Update failed", "Could not update the selected filament color.")
            return
        if self.last_saved_record_id == record_id:
            self.hex_input.setText(color)
        self.scan_status.setText(f"Updated filament #{record_id} color to {color}.")
        self.refresh_table()

    def closeEvent(self, event) -> None:  # pragma: no cover - Qt close path
        if self.scan_worker is not None and self.scan_worker.isRunning():
            self.scan_worker.requestInterruption()
            self.scan_worker.wait(500)
        self.connection.close()
        super().closeEvent(event)


def main() -> int:
    app = QApplication([])
    window = FilamentDbWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
