import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl

from backend import Backend

app = QApplication(sys.argv)

engine = QQmlApplicationEngine()

backend = Backend()

engine.rootContext().setContextProperty(
    "backend",
    backend
)

engine.load(
    QUrl.fromLocalFile(
        "qml/Main.qml"
    )
)

if not engine.rootObjects():
    sys.exit(-1)

sys.exit(app.exec())