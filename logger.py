# logger.py — centralized logging for ATLAS

from PySide6 import QtWidgets

class Logger:
    def __init__(self, text_box: QtWidgets.QPlainTextEdit, status_bar: QtWidgets.QStatusBar):
        self.text_box = text_box
        self.status_bar = status_bar

    def log(self, msg: str, error: bool = False):
        prefix = "[ERROR] " if error else ""
        self.text_box.appendPlainText(prefix + msg)
        self.status_bar.showMessage(msg, 6000)
        print(msg)
