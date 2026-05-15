"""Main window — wires the 4 wizard pages and the shared AppState."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .pages import ClusterPage, EncryptPage, ResultsPage, SourcePage
from .state import AppState


_STEPS = ["1. Source", "2. Encrypt", "3. Cluster", "4. Results"]


class _StepHeader(QWidget):
    """Tiny breadcrumb of the four steps, highlighting the current one."""

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        self._labels = []
        for i, name in enumerate(_STEPS):
            lbl = QLabel(name)
            lbl.setStyleSheet("padding: 4px 10px; border-radius: 4px;")
            self._labels.append(lbl)
            layout.addWidget(lbl)
            if i < len(_STEPS) - 1:
                sep = QLabel("›"); sep.setStyleSheet("color: #94a3b8;")
                layout.addWidget(sep)
        layout.addStretch(1)
        self.set_current(0)

    def set_current(self, idx: int) -> None:
        for i, lbl in enumerate(self._labels):
            if i == idx:
                lbl.setStyleSheet("padding: 4px 10px; border-radius: 4px; background: #0d6efd; color: white; font-weight: 600;")
            elif i < idx:
                lbl.setStyleSheet("padding: 4px 10px; border-radius: 4px; color: #475569;")
            else:
                lbl.setStyleSheet("padding: 4px 10px; border-radius: 4px; color: #94a3b8;")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CryptTraject — privacy-preserving clustering")
        self.resize(820, 640)

        self.state = AppState()

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = _StepHeader()
        root.addWidget(self.header)

        self.stack = QStackedWidget()
        self.source_page = SourcePage(self.state)
        self.encrypt_page = EncryptPage(self.state)
        self.cluster_page = ClusterPage(self.state)
        self.results_page = ResultsPage(self.state)
        for p in (self.source_page, self.encrypt_page, self.cluster_page, self.results_page):
            self.stack.addWidget(p)
        root.addWidget(self.stack, 1)

        self.setCentralWidget(central)
        status = QStatusBar()
        status.showMessage("Ready. Secret keys never leave this machine.")
        self.setStatusBar(status)

        # ---- navigation wiring ----
        self.source_page.next_requested.connect(lambda: self._goto(1))
        self.encrypt_page.back_requested.connect(lambda: self._goto(0))
        self.encrypt_page.next_requested.connect(lambda: self._goto(2))
        self.cluster_page.back_requested.connect(lambda: self._goto(1))
        self.cluster_page.next_requested.connect(lambda: self._goto(3))
        self.results_page.restart_requested.connect(self._restart)

    def _goto(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)
        self.header.set_current(idx)
        page = self.stack.currentWidget()
        if hasattr(page, "on_show"):
            page.on_show()

    def _restart(self) -> None:
        # Fresh state, fresh pages. Cheaper to rebuild than reset every widget.
        self.state = AppState()
        new_window = MainWindow()
        new_window.show()
        self.close()


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
