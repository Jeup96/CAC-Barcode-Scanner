from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
    Property
)

from barcode import (
    parse_cac_barcode,
    BarcodeFormatError
)

from database import Database

from personnel_model import PersonnelModel


class Backend(QObject):

    logAdded = Signal(str)
    checkoutRequested = Signal(str)

    countsChanged = Signal()

    def __init__(self):

        super().__init__()

        self.db = Database()

        self._personnelModel = PersonnelModel()

        self.pending_name = ""
        self.pending_rank = ""

        self.refreshPersonnel()

    @Property(QObject, constant=True)
    def personnelModel(self):

        return self._personnelModel

    def refreshPersonnel(self):

        rows = self.db.get_all_personnel()

        personnel = []

        for row in rows:

            personnel.append(
                {
                    "name": row[0],
                    "rank": row[1],
                    "status": row[2],
                    "location": row[3]
                }
            )

        self._personnelModel.loadData(
            personnel
        )

        self.countsChanged.emit()

    @Slot(str)
    def processBarcode(self, raw):

        raw = raw.strip()

        if not raw:
            return

        try:

            holder = parse_cac_barcode(raw)

            fullname = holder.full_name
            rank = holder.rank

            person = self.db.get_person(
                fullname
            )

            if person and person[3] == "IN":

                self.pending_name = fullname
                self.pending_rank = rank

                self.checkoutRequested.emit(
                    fullname
                )

                return

            self.db.check_in(
                fullname,
                rank
            )

            self.refreshPersonnel()

            self.logAdded.emit(
                f"✓ {fullname} checked IN"
            )

        except BarcodeFormatError as e:

            self.logAdded.emit(
                str(e)
            )

    @Slot(str)
    def completeCheckout(self, location):

        if not self.pending_name:
            return

        self.db.check_out(
            self.pending_name,
            self.pending_rank,
            location
        )

        self.refreshPersonnel()

        self.logAdded.emit(
            f"↗ {self.pending_name} → {location}"
        )

        self.pending_name = ""
        self.pending_rank = ""

    @Slot()
    def clearRoster(self):

        self.db.clear_all()

        self.refreshPersonnel()

        self.logAdded.emit(
            "Roster Cleared"
        )

    @Slot(result=int)
    def activeCount(self):

        return self.db.count_in()

    @Slot(result=int)
    def outCount(self):

        return self.db.count_out()

    @Slot(result=int)
    def totalCount(self):

        return self.db.total_count()

    @Slot(result=int)
    def scanCount(self):

        return self.db.scan_count()

    @Slot(result=str)
    def lastScanName(self):

        row = self.db.last_scan()

        if not row:
            return "No Scans"

        return row[0]

    @Slot()
    def exportRoster(self):

        self.db.export_roster_csv()

        self.logAdded.emit(
            "Roster exported."
        )

    @Slot()
    def exportActivity(self):

        self.db.export_activity_csv()

        self.logAdded.emit(
            "Activity exported."
        )