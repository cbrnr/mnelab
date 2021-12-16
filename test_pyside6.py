from PySide6.QtCore import QTimer, SLOT
from PySide6.QtWidgets import QApplication, QLabel

app = QApplication()
label = QLabel("1")
label.show()
QTimer.singleShot(1000, app, SLOT("quit()"))
app.exec()
