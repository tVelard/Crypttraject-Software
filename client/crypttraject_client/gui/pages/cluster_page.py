"""Page 3 — run clustering on the server, decrypt results locally."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..state import AppState
from ..workers import ClusterWorker, run_in_thread


class ClusterPage(QWidget):
    back_requested = Signal()
    next_requested = Signal()

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._thread = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.addWidget(QLabel(
            "<h2>Step 3 — Cluster</h2>"
            "<p>The server computes <code>(sig_A − sig_B)²</code> on the ciphertexts. "
            "It cannot decrypt them. Results come back to us, we decrypt locally "
            "and assemble the cluster assignment.</p>"
        ))

        box = QGroupBox("Threshold")
        form = QFormLayout(box)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.05, 0.95); self.threshold.setSingleStep(0.05); self.threshold.setValue(0.5)
        form.addRow("Jaccard threshold:", self.threshold)
        root.addWidget(box)

        self.progress = QProgressBar(); self.progress.setRange(0, 0); self.progress.hide()
        root.addWidget(self.progress)

        self.log_box = QPlainTextEdit(); self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background:#0f172a; color:#a8d8ea; font-family: Consolas, monospace; font-size: 11px;")
        root.addWidget(self.log_box, 1)

        footer = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self.back_requested.emit)
        footer.addWidget(self.back_btn)
        footer.addStretch(1)
        self.run_btn = QPushButton("Run clustering")
        self.run_btn.clicked.connect(self._on_run)
        footer.addWidget(self.run_btn)
        self.next_btn = QPushButton("Next — Results")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self.next_requested.emit)
        footer.addWidget(self.next_btn)
        root.addLayout(footer)

    def _append_log(self, msg: str) -> None:
        self.log_box.appendPlainText(msg)

    def _on_run(self) -> None:
        self.state.threshold = float(self.threshold.value())
        self.run_btn.setEnabled(False); self.back_btn.setEnabled(False)
        self.progress.show()

        worker = ClusterWorker(self.state)
        worker.log.connect(self._append_log)
        worker.failed.connect(self._on_failed)
        worker.done.connect(self._on_done)
        self._thread = run_in_thread(worker)

    def _on_done(self, clusters: dict) -> None:
        self.state.clusters = clusters
        self.progress.hide()
        self.run_btn.setEnabled(True); self.back_btn.setEnabled(True)
        self.next_btn.setEnabled(True)

    def _on_failed(self, msg: str) -> None:
        self._append_log(f"[ERROR] {msg}")
        self.progress.hide()
        self.run_btn.setEnabled(True); self.back_btn.setEnabled(True)
