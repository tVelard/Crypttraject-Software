"""Main window — wires the three screens (config → run → map).

Config and the shared AppState flow forward: the user configures a run,
the run screen drives the workers, and on success the map screen renders
the decrypted clusters. Secret keys and decryption never leave this host.
"""

from __future__ import annotations

import sys

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

from .pages import ConfigPage, MapPage, RunPage
from .state import AppState


_STEPS = ["1. Configuration", "2. Exécution", "3. Visualisation"]


class _StepHeader(QWidget):
    """Tiny breadcrumb of the three steps, highlighting the current one."""

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        self._labels = []
        for i, name in enumerate(_STEPS):
            lbl = QLabel(name)
            lbl.setStyleSheet("padding: 4px 10px; border-radius: 4px;")
            self._labels.append(lbl)
            layout.addWidget(lbl)
            if i < len(_STEPS) - 1:
                sep = QLabel("›")
                sep.setStyleSheet("color: #94a3b8;")
                layout.addWidget(sep)
        layout.addStretch(1)
        self.set_current(0)

    def set_current(self, idx: int) -> None:
        for i, lbl in enumerate(self._labels):
            if i == idx:
                lbl.setStyleSheet(
                    "padding: 4px 10px; border-radius: 4px; "
                    "background: #0d6efd; color: white; font-weight: 600;"
                )
            elif i < idx:
                lbl.setStyleSheet("padding: 4px 10px; border-radius: 4px; color: #475569;")
            else:
                lbl.setStyleSheet("padding: 4px 10px; border-radius: 4px; color: #94a3b8;")


class MainWindow(QMainWindow):
    PAGE_CONFIG, PAGE_RUN, PAGE_MAP = range(3)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CryptTraject — clustering préservant la vie privée")
        self.resize(960, 720)

        self.state = AppState()

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = _StepHeader()
        root.addWidget(self.header)

        self.stack = QStackedWidget()
        self.config_page = ConfigPage(self.state)
        self.run_page = RunPage(self.state)
        self.map_page = MapPage(self.state)
        for p in (self.config_page, self.run_page, self.map_page):
            self.stack.addWidget(p)
        root.addWidget(self.stack, 1)

        self.setCentralWidget(central)
        status = QStatusBar()
        status.showMessage("Prêt. La clé secrète ne quitte jamais cette machine.")
        self.setStatusBar(status)

        # ---- navigation wiring ----
        self.config_page.run_requested.connect(self._start_run)
        self.run_page.completed.connect(lambda: self._goto(self.PAGE_MAP))
        self.run_page.back_requested.connect(lambda: self._goto(self.PAGE_CONFIG))
        self.map_page.restart_requested.connect(lambda: self._goto(self.PAGE_CONFIG))

    def _goto(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)
        self.header.set_current(idx)
        page = self.stack.currentWidget()
        if hasattr(page, "on_show"):
            page.on_show()

    def _start_run(self) -> None:
        self._goto(self.PAGE_RUN)
        self.run_page.start()


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
