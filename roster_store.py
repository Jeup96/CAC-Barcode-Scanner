"""
Persistence layer for the CAC roster workbook.

Uses a live Excel window via pywin32 when available (so staff can watch
the sheet update in real time). Falls back to plain openpyxl file I/O
on machines without Excel/pywin32 installed.
"""
from __future__ import annotations

import csv
import logging
import os
from datetime import datetime
from typing import Optional

import openpyxl

try:
    import win32com.client as win32
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

logger = logging.getLogger(__name__)

HEADERS = ["Full Name", "Rank", "Time In", "Time Out", "Location"]
SUMMARY_HEADERS = ["Full Name", "Rank", "Status"]
SHEET_NAME = "Sheet"
TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"


class RosterStore:
    def __init__(self, filepath: str):
        self.filepath = os.path.abspath(filepath)
        self._ensure_file_exists()

        self.use_com = HAS_WIN32
        self.excel = None
        self.workbook = None
        self.sheet = None
        self.summary = None

        if self.use_com:
            try:
                self._open_live()
            except Exception:
                logger.exception("Excel COM automation failed, falling back to file mode.")
                self.use_com = False

        if not self.use_com:
            self._open_headless()

    # ---------- setup ----------

    def _ensure_file_exists(self):
        if os.path.exists(self.filepath):
            return
        wb = openpyxl.Workbook()
        sheet = wb.active
        sheet.title = SHEET_NAME
        for col, header in enumerate(HEADERS, start=1):
            sheet.cell(row=1, column=col, value=header)
        summary = wb.create_sheet("Summary")
        for col, header in enumerate(SUMMARY_HEADERS, start=1):
            summary.cell(row=1, column=col, value=header)
        wb.save(self.filepath)

    def _open_live(self):
        self.excel = win32.Dispatch("Excel.Application")
        self.excel.Visible = True
        self.workbook = self.excel.Workbooks.Open(self.filepath)
        self.sheet = self.workbook.Worksheets(SHEET_NAME)
        if not any(ws.Name == "Summary" for ws in self.workbook.Worksheets):
            summary = self.workbook.Worksheets.Add()
            summary.Name = "Summary"
            for col, header in enumerate(SUMMARY_HEADERS, start=1):
                summary.Cells(1, col).Value = header
        self.summary = self.workbook.Worksheets("Summary")

    def _open_headless(self):
        self.workbook = openpyxl.load_workbook(self.filepath)
        self.sheet = self.workbook[SHEET_NAME]
        if "Summary" not in self.workbook.sheetnames:
            self.summary = self.workbook.create_sheet("Summary")
            for col, header in enumerate(SUMMARY_HEADERS, start=1):
                self.summary.cell(row=1, column=col, value=header)
        else:
            self.summary = self.workbook["Summary"]

    # ---------- cell access shims (COM vs openpyxl) ----------

    def _get(self, sheet, row, col):
        return sheet.Cells(row, col).Value if self.use_com else sheet.cell(row=row, column=col).value

    def _set(self, sheet, row, col, value):
        if self.use_com:
            sheet.Cells(row, col).Value = value
        else:
            sheet.cell(row=row, column=col).value = value

    def _last_row(self, sheet) -> int:
        return sheet.UsedRange.Rows.Count if self.use_com else sheet.max_row

    def _save(self):
        if self.use_com:
            self.workbook.Save()
        else:
            self.workbook.save(self.filepath)

    # ---------- public operations ----------

    def find_open_entry(self, fullname: str) -> Optional[int]:
        """Row number of the most recent entry for fullname with no Time Out, or None."""
        for row in range(self._last_row(self.sheet), 1, -1):
            if self._get(self.sheet, row, 1) == fullname:
                timeout = self._get(self.sheet, row, 4)
                return row if not timeout or str(timeout).strip() == "" else None
        return None

    def check_in(self, fullname: str, rank: str) -> int:
        row = self._last_row(self.sheet) + 1
        self._set(self.sheet, row, 1, fullname)
        self._set(self.sheet, row, 2, rank)
        self._set(self.sheet, row, 3, datetime.now().strftime(TIMESTAMP_FMT))
        self._set(self.sheet, row, 4, None)
        self._set(self.sheet, row, 5, None)
        self._rebuild_summary()
        self._save()
        return row

    def check_out(self, row: int, location: str) -> None:
        self._set(self.sheet, row, 4, datetime.now().strftime(TIMESTAMP_FMT))
        self._set(self.sheet, row, 5, location)
        self._rebuild_summary()
        self._save()

    def clear(self) -> None:
        for row in range(2, self._last_row(self.sheet) + 1):
            for col in range(1, 6):
                self._set(self.sheet, row, col, None)
        self._rebuild_summary()
        self._save()

    def export_csv(self, csv_path: str) -> None:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
            for row in range(2, self._last_row(self.sheet) + 1):
                values = [self._get(self.sheet, row, c) for c in range(1, 6)]
                if any(v not in (None, "") for v in values):
                    writer.writerow(values)

    def _rebuild_summary(self) -> None:
        """Recompute one row per person showing their current IN/OUT status."""
        latest: dict[str, tuple[str, str]] = {}
        for row in range(2, self._last_row(self.sheet) + 1):
            name = self._get(self.sheet, row, 1)
            if not name:
                continue
            rank = self._get(self.sheet, row, 2)
            timeout = self._get(self.sheet, row, 4)
            status = "OUT" if timeout and str(timeout).strip() else "IN"
            latest[name] = (rank, status)  # later rows overwrite earlier ones

        for row in range(2, self._last_row(self.summary) + 1):
            for col in range(1, 4):
                self._set(self.summary, row, col, None)

        for i, (name, (rank, status)) in enumerate(sorted(latest.items()), start=2):
            self._set(self.summary, i, 1, name)
            self._set(self.summary, i, 2, rank)
            self._set(self.summary, i, 3, status)

    def close(self) -> None:
        if self.use_com:
            try:
                self.workbook.Save()
            except Exception:
                logger.exception("Error saving workbook on close.")
