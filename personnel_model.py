from PySide6.QtCore import (
    Qt,
    QAbstractListModel,
    QModelIndex
)


class PersonnelModel(QAbstractListModel):

    NameRole = Qt.UserRole + 1
    RankRole = Qt.UserRole + 2
    StatusRole = Qt.UserRole + 3
    LocationRole = Qt.UserRole + 4

    def __init__(self):
        super().__init__()

        self._people = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._people)

    def data(self, index, role):

        if not index.isValid():
            return None

        person = self._people[index.row()]

        if role == self.NameRole:
            return person["name"]

        if role == self.RankRole:
            return person["rank"]

        if role == self.StatusRole:
            return person["status"]

        if role == self.LocationRole:
            return person["location"]

        return None

    def roleNames(self):

        return {
            self.NameRole: b"name",
            self.RankRole: b"rank",
            self.StatusRole: b"status",
            self.LocationRole: b"location"
        }

    def loadData(self, personnel):

        self.beginResetModel()

        self._people = personnel

        self.endResetModel()