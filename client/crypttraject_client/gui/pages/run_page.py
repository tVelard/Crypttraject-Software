"""Screen 2 — run the pipeline and show live progress per step.

The three workers (ingest → encrypt/upload → cluster) run back-to-back on
their own threads. This screen renders them as a checklist where each step
shows a spinner while running, a live timer, and a ✓/✗ when it settles.
There is no byte-level progress bar — the steps + timers are the feedback.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, QThread, QTimer, Signal
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
        # Keep a strong reference to every (worker, thread) pair until the
        # thread has actually finished and been destroyed. Dropping the last
        # Python reference to a still-running QThread crashes the process with
        # "QThread: Destroyed while thread is still running".
        self._jobs: list = []
        self._current_step = self.STEP_INGEST
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
        # IMPORTANT: every slot below must be a *bound method of this QObject*
        # (which lives on the GUI thread), NEVER a lambda. A lambda has no
        # QObject receiver, so Qt has no target thread to queue the call onto
        # and runs it directly inside the worker thread — touching widgets /
        # timers / the painter off-thread, which crashes the process. Bound
        # methods carry this widget's thread affinity, so cross-thread signals
        # are auto-queued onto the GUI thread.
        self._current_step = step
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
        worker.failed.connect(self._on_worker_failed)

        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        # Tear down in order: worker.finished -> thread.quit, then once the
        # thread has fully stopped, drop our reference. We hold the pair in
        # self._jobs until the thread is destroyed so it can never be
        # garbage-collected while still running.
        worker.finished.connect(thread.quit)
        self._jobs.append((worker, thread))
        thread.finished.connect(self._on_thread_finished)
        thread.start()

    def _on_worker_failed(self, message: str) -> None:
        """Worker.failed slot (GUI thread). Uses the step that was running."""
        self._step_failed(self._current_step, message)

    def _on_thread_finished(self) -> None:
        """A QThread finished — drop any of our jobs whose thread has stopped."""
        for job in list(self._jobs):
            _worker, thread = job
            if thread.isFinished():
                self._jobs.remove(job)
                _worker.deleteLater()
                thread.deleteLater()

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
