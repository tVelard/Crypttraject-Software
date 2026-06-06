"""Screen 2 — run the pipeline and show live progress per step.

The three workers (ingest → encrypt/upload → cluster) run back-to-back on
their own threads. This screen renders them as a checklist where each step
shows a spinner while running, a live timer, and a ✓/✗ when it settles.
There is no byte-level progress bar — the steps + timers are the feedback.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..state import AppState
from ..workers import (
    ClusterWorker,
    EncryptUploadWorker,
    IngestWorker,
    run_in_thread,
)


_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class _StepRow(QWidget):
    """One line in the checklist: [state icon] label … [timer]."""

    PENDING, RUNNING, DONE, FAILED = range(4)

    def __init__(self, title: str):
        super().__init__()
        self.title = title
        self._state = self.PENDING
        self._spin = 0
        self._elapsed = 0.0

        row = QHBoxLayout(self)
        row.setContentsMargins(4, 2, 4, 2)
        self.icon = QLabel("○")
        self.icon.setFixedWidth(20)
        self.icon.setAlignment(Qt.AlignCenter)
        self.label = QLabel(title)
        self.timer_lbl = QLabel("")
        self.timer_lbl.setStyleSheet("color: #64748b;")
        row.addWidget(self.icon)
        row.addWidget(self.label, 1)
        row.addWidget(self.timer_lbl)
        self._restyle()

    def set_state(self, state: int) -> None:
        self._state = state
        self._restyle()

    def tick(self, dt: float) -> None:
        if self._state == self.RUNNING:
            self._elapsed += dt
            self._spin = (self._spin + 1) % len(_SPINNER)
            self.icon.setText(_SPINNER[self._spin])
            self.timer_lbl.setText(f"{self._elapsed:0.1f}s")

    def _restyle(self) -> None:
        if self._state == self.PENDING:
            self.icon.setText("○")
            self.icon.setStyleSheet("color: #94a3b8;")
            self.label.setStyleSheet("color: #94a3b8;")
        elif self._state == self.RUNNING:
            self.icon.setStyleSheet("color: #0d6efd;")
            self.label.setStyleSheet("color: #0f172a; font-weight: 600;")
        elif self._state == self.DONE:
            self.icon.setText("✓")
            self.icon.setStyleSheet("color: #16a34a;")
            self.label.setStyleSheet("color: #334155;")
        else:  # FAILED
            self.icon.setText("✗")
            self.icon.setStyleSheet("color: #dc2626;")
            self.label.setStyleSheet("color: #dc2626; font-weight: 600;")


class RunPage(QWidget):
    # Emitted once the whole pipeline succeeds — main window switches to map.
    completed = Signal()
    back_requested = Signal()

    STEP_INGEST, STEP_ENCRYPT, STEP_CLUSTER = range(3)

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._thread = None
        self._worker = None
        self._build()

        # ~10 Hz UI tick drives the spinners + timers.
        self._anim = QTimer(self)
        self._anim.setInterval(100)
        self._anim.timeout.connect(self._on_tick)

    # ------------------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 12)

        self.title = QLabel("<h2>Clustering en cours…</h2>")
        root.addWidget(self.title)

        self.steps: List[_StepRow] = [
            _StepRow("Lecture + chiffrement local des données"),
            _StepRow("Envoi des signatures chiffrées au serveur"),
            _StepRow("Calcul serveur + déchiffrement local"),
        ]
        for s in self.steps:
            root.addWidget(s)

        self.bar = QProgressBar()
        self.bar.setRange(0, 0)          # indeterminate marquee while running
        self.bar.setTextVisible(False)
        root.addWidget(self.bar)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b91c1c; font-weight: 600;")
        self.error_label.setWordWrap(True)
        root.addWidget(self.error_label)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; color: #475569;")
        root.addWidget(self.log, 1)

        footer = QHBoxLayout()
        self.back_btn = QPushButton("‹ Reconfigurer")
        self.back_btn.clicked.connect(self.back_requested.emit)
        self.back_btn.setEnabled(False)
        footer.addWidget(self.back_btn)
        footer.addStretch(1)
        root.addLayout(footer)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Reset UI and kick off the first worker."""
        self.state.reset_run()
        self.log.clear()
        self.error_label.setText("")
        self.title.setText("<h2>Clustering en cours…</h2>")
        self.bar.setRange(0, 0)
        self.back_btn.setEnabled(False)
        for s in self.steps:
            s.set_state(_StepRow.PENDING)
            s.timer_lbl.setText("")
        self._anim.start()
        self._run_step(self.STEP_INGEST)

    def _on_tick(self) -> None:
        for s in self.steps:
            s.tick(0.1)

    def _append_log(self, line: str) -> None:
        self.log.appendPlainText(line)

    # ------------------------------------------------------------------
    # Step orchestration
    # ------------------------------------------------------------------

    def _run_step(self, step: int) -> None:
        self.steps[step].set_state(_StepRow.RUNNING)
        if step == self.STEP_INGEST:
            worker = IngestWorker(self.state)
            worker.done.connect(self._ingest_done)
        elif step == self.STEP_ENCRYPT:
            worker = EncryptUploadWorker(self.state)
            worker.done.connect(self._encrypt_done)
        else:
            worker = ClusterWorker(self.state)
            worker.done.connect(self._cluster_done)
        worker.log.connect(self._append_log)
        worker.failed.connect(lambda msg, s=step: self._step_failed(s, msg))
        self._worker = worker
        self._thread = run_in_thread(worker)

    def _ingest_done(self, signatures: dict, points: dict) -> None:
        self.state.signatures = signatures
        self.state.record_points = points
        if len(signatures) < 2:
            self._step_failed(self.STEP_INGEST, "Need at least 2 records to cluster.")
            return
        self.steps[self.STEP_INGEST].set_state(_StepRow.DONE)
        self._run_step(self.STEP_ENCRYPT)

    def _encrypt_done(self, _session_id: str) -> None:
        self.steps[self.STEP_ENCRYPT].set_state(_StepRow.DONE)
        self._run_step(self.STEP_CLUSTER)

    def _cluster_done(self, clusters: dict) -> None:
        self.state.clusters = clusters
        self.steps[self.STEP_CLUSTER].set_state(_StepRow.DONE)
        self._finish_ok()

    # ------------------------------------------------------------------
    # Terminal states
    # ------------------------------------------------------------------

    def _finish_ok(self) -> None:
        self._anim.stop()
        self.bar.setRange(0, 1)
        self.bar.setValue(1)
        n_clusters = len(set(self.state.clusters.values()))
        self.title.setText(
            f"<h2>✓ Terminé — {n_clusters} clusters sur "
            f"{len(self.state.clusters)} enregistrements</h2>"
        )
        self.back_btn.setEnabled(True)
        self.completed.emit()

    def _step_failed(self, step: int, message: str) -> None:
        self._anim.stop()
        self.steps[step].set_state(_StepRow.FAILED)
        self.bar.setRange(0, 1)
        self.bar.setValue(0)
        self.title.setText("<h2>✗ Échec</h2>")
        self.error_label.setText(message)
        self._append_log(f"[error] {message}")
        self.back_btn.setEnabled(True)
