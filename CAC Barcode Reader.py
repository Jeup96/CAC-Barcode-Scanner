from __future__ import annotations

import os
import logging

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QListWidget,
    QVBoxLayout, QHBoxLayout, QMessageBox, QComboBox, QDialog
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt

from barcode import BarcodeFormatError, parse_cac_barcode
from roster_store import RosterStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

LOCATIONS = ["Lunch", "HHQ", "Extension Site", "Bathroom", "Offsite"]
ROSTER_FILE = "CAC_Roster.xlsx"
ICON_FILE = "airforce.ico"
BACKGROUND_FILE = "airforce_background.jpg"


# -------------------- LOCATION DIALOG --------------------

class LocationDialog(QDialog):
    def __init__(self, fullname: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Location")
        self.setFixedSize(350, 180)

        layout = QVBoxLayout()

        label = QLabel(f"Where is {fullname} headed?")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        self.combo = QComboBox()
        self.combo.addItems(LOCATIONS)
        layout.addWidget(self.combo)

        confirm_btn = QPushButton("Confirm")
        confirm_btn.clicked.connect(self.accept)
        layout.addWidget(confirm_btn)

        self.setLayout(layout)

    def get_location(self):
        return self.combo.currentText()


# -------------------- MAIN APP --------------------

class BarcodeApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CAC Barcode Reader (PyQt Version)")
        self.setMinimumSize(800, 300)
        self.collapsed_size = (800, 150)
        self.expanded_size = (800, 300)

        if os.path.exists(ICON_FILE):
            self.setWindowIcon(QIcon(ICON_FILE))

        self.store = RosterStore(ROSTER_FILE)

        self._build_ui()

    # ---------- UI SETUP ----------

    def _build_ui(self):
        main_layout = QVBoxLayout()

        # Background image
        if os.path.exists(BACKGROUND_FILE):
            bg_label = QLabel()
            pixmap = QPixmap(BACKGROUND_FILE)
            bg_label.setPixmap(pixmap.scaled(self.width(), self.height(), Qt.AspectRatioMode.IgnoreAspectRatio))
            bg_label.setScaledContents(True)
            main_layout.addWidget(bg_label)

        header = QLabel("Scan the FRONT of your government-issued ID:")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 22px; font-weight: bold;")
        main_layout.addWidget(header)

        # Barcode entry
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Paste or scan barcode here...")
        self.entry.setStyleSheet("font-size: 18px; padding: 6px;")
        self.entry.returnPressed.connect(self.process_barcode)
        main_layout.addWidget(self.entry)

        # Log container
        self.log_container = QVBoxLayout()
        self.log_list = QListWidget()
        self.log_list.setStyleSheet("font-size: 12px;")
        self.log_container.addWidget(self.log_list)

        main_layout.addLayout(self.log_container)


        # Buttons
        btn_row = QHBoxLayout()

        clear_btn = QPushButton("Clear Roster")
        clear_btn.clicked.connect(self.clear_roster)
        btn_row.addWidget(clear_btn)

        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self.export_csv)
        btn_row.addWidget(export_btn)

        # Show/Hide Log button
        self.toggle_log_btn = QPushButton("Hide Log")
        self.toggle_log_btn.clicked.connect(self.toggle_log)
        btn_row.addWidget(self.toggle_log_btn)

        main_layout.addLayout(btn_row)


        self.setLayout(main_layout)

    # ---------- LOGGING ----------

    def toggle_log(self):
        if self.log_list.isVisible():
            self.log_list.hide()
            self.toggle_log_btn.setText("Show Log")

            # shrink window
            self.setFixedSize(*self.collapsed_size)

        else:
            self.log_list.show()
            self.toggle_log_btn.setText("Hide Log")

            # expand window
            self.setFixedSize(*self.expanded_size)

    def _log(self, msg: str):
        self.log_list.addItem(msg)
        self.log_list.scrollToBottom()

    # ---------- BARCODE PROCESSING ----------

    def process_barcode(self):
        raw = self.entry.text().strip()
        self.entry.clear()

        if not raw:
            return

        try:
            holder = parse_cac_barcode(raw)
        except BarcodeFormatError as exc:
            QMessageBox.critical(self, "Scan Error", str(exc))
            return
        except Exception:
            logger.exception("Unexpected barcode error")
            QMessageBox.critical(self, "Scan Error", "Could not read that barcode.")
            return

        fullname, rank = holder.full_name, holder.rank

        try:
            open_row = self.store.find_open_entry(fullname)
            if open_row:
                dialog = LocationDialog(fullname, self)
                if dialog.exec():
                    location = dialog.get_location()
                    self._finish_checkout(open_row, fullname, location)
                return

            self.store.check_in(fullname, rank)
            self._log(f"Time In recorded for {fullname} ({rank})")

        except Exception:
            logger.exception("Roster update error")
            QMessageBox.critical(self, "Roster Error", "Could not update the roster file.")

    def _finish_checkout(self, row: int, fullname: str, location: str):
        try:
            self.store.check_out(row, location)
            self._log(f"Timeout recorded for {fullname} at {location}")
        except Exception:
            logger.exception("Checkout error")
            QMessageBox.critical(self, "Roster Error", "Could not update the roster file.")

    # ---------- ACTIONS ----------

    def clear_roster(self):
        if QMessageBox.question(self, "Clear Roster", "Clear all entries for a new day?") != QMessageBox.StandardButton.Yes:
            return

        try:
            self.store.clear()
            self.log_list.clear()
            QMessageBox.information(self, "Roster Cleared", "Roster has been cleared.")
        except Exception:
            logger.exception("Clear error")
            QMessageBox.critical(self, "Roster Error", "Could not clear the roster.")

    def export_csv(self):
        try:
            path = os.path.splitext(ROSTER_FILE)[0] + "_export.csv"
            self.store.export_csv(path)
            QMessageBox.information(self, "Exported", f"Roster exported to {path}")
        except Exception:
            logger.exception("Export error")
            QMessageBox.critical(self, "Export Error", "Could not export the roster.")


# -------------------- MAIN --------------------

if __name__ == "__main__":
    app = QApplication([])
    window = BarcodeApp()
    window.show()
    app.exec()
