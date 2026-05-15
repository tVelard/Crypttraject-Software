"""Page 2 — local parsing + MinHash + BFV encryption + upload."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..state import AppState
from ..workers import EncryptUploadWorker, IngestWorker, run_in_thread


class EncryptPage(QWidget):
    back_requested = Signal()
    next_requested = Signal()

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._thread = None
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        root.addWidget(QLabel(
            "<h2>Step 2 — Encrypt & upload</h2>"
            "<p>The secret key is generated and kept locally. "
            "Only the public key, BFV context, and ciphertexts leave this machine.</p>"
        ))

        # --- LSH params ---
        lsh_box = QGroupBox("LSH parameters")
        lsh_form = QFormLayout(lsh_box)
        self.bands = QSpinBox(); self.bands.setRange(1, 1024); self.bands.setValue(16)
        self.rows = QSpinBox(); self.rows.setRange(1, 1024); self.rows.setValue(8)
        self.bands.valueChanged.connect(self._validate_lsh)
        self.rows.valueChanged.connect(self._validate_lsh)
        lsh_form.addRow("Bands (b):", self.bands)
        lsh_form.addRow("Rows / band (r):", self.rows)
        self.lsh_warn = QLabel(""); self.lsh_warn.setStyleSheet("color: #b91c1c;")
        lsh_form.addRow("", self.lsh_warn)
        root.addWidget(lsh_box)

        # --- Server + keys ---
        srv_box = QGroupBox("Server & key persistence")
        srv_form = QFormLayout(srv_box)
        self.server_url = QLineEdit("http://localhost:8000")
        srv_form.addRow("Server URL:", self.server_url)

        key_row = QHBoxLayout()
        self.key_dir = QLineEdit()
        self.key_dir.setPlaceholderText("optional — directory to save/reuse the BFV session")
        key_browse = QPushButton("Browse…")
        key_browse.clicked.connect(self._browse_keys)
        key_row.addWidget(self.key_dir, 1)
        key_row.addWidget(key_browse)
        srv_form.addRow("Key directory:", key_row)
        root.addWidget(srv_box)

        # --- Progress + log ---
        # Range (0, 0) means "indeterminate" by default. The worker upgrades
        # us to (0, total) as soon as it knows the record count.
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%v / %m")
        self.progress.hide()
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #475569; font-size: 11px;")
        self.progress_label.hide()
        root.addWidget(self.progress)
        root.addWidget(self.progress_label)

        self.log_box = QPlainTextEdit(); self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background:#0f172a; color:#a8d8ea; font-family: Consolas, monospace; font-size: 11px;")
        root.addWidget(self.log_box, 1)

        # --- Footer ---
        footer = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self.back_requested.emit)
        footer.addWidget(self.back_btn)
        footer.addStretch(1)
        self.run_btn = QPushButton("Encrypt && upload")
        self.run_btn.clicked.connect(self._on_run)
        footer.addWidget(self.run_btn)
        self.next_btn = QPushButton("Next — Cluster")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self.next_requested.emit)
        footer.addWidget(self.next_btn)
        root.addLayout(footer)

    # ------------------------------------------------------------------

    def _validate_lsh(self) -> None:
        if self.bands.value() * self.rows.value() != self.state.num_perm:
            self.lsh_warn.setText(
                f"bands × rows = {self.bands.value() * self.rows.value()} ≠ num_perm = {self.state.num_perm}"
            )
        else:
            self.lsh_warn.setText("")

    def _browse_keys(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Pick a directory to persist BFV keys")
        if path:
            self.key_dir.setText(path)

    def on_show(self) -> None:
        """Called when the page becomes visible — sync defaults that depend on state."""
        self._validate_lsh()

    # ------------------------------------------------------------------

    def _append_log(self, msg: str) -> None:
        self.log_box.appendPlainText(msg)

    def _on_run(self) -> None:
        if self.bands.value() * self.rows.value() != self.state.num_perm:
            self._append_log(f"[ERROR] {self.lsh_warn.text()}")
            return

        self.state.bands = self.bands.value()
        self.state.rows_per_band = self.rows.value()
        self.state.server_url = self.server_url.text().strip() or "http://localhost:8000"
        kd = self.key_dir.text().strip()
        self.state.key_dir = Path(kd) if kd else None

        self.run_btn.setEnabled(False); self.back_btn.setEnabled(False)
        self._reset_progress()
        self.progress.show()
        self.progress_label.show()
        self._append_log("[ingest] parsing source and computing MinHash signatures...")

        worker = IngestWorker(self.state)
        worker.log.connect(self._append_log)
        worker.failed.connect(self._on_failed)
        worker.progress.connect(self._on_progress)
        worker.done.connect(self._on_ingest_done)
        self._thread = run_in_thread(worker)

    def _on_ingest_done(self, sigs: dict) -> None:
        self.state.signatures = sigs
        if len(sigs) < 2:
            self._on_failed("Need at least 2 records to cluster.")
            return
        # Hand off to the encryption phase: switch the bar to indeterminate
        # (BFV.encryptInt is fast but we don't easily know per-ciphertext progress).
        self.progress.setRange(0, 0)
        self.progress_label.setText("Encrypting and uploading...")
        self._append_log(f"[encrypt] {len(sigs)} signatures → BFV → server")
        worker = EncryptUploadWorker(self.state)
        worker.log.connect(self._append_log)
        worker.failed.connect(self._on_failed)
        worker.done.connect(self._on_upload_done)
        self._thread = run_in_thread(worker)

    def _on_progress(self, current: int, total: int, message: str) -> None:
        if total > 0:
            # Determinate mode: real progress bar.
            self.progress.setRange(0, total)
            self.progress.setValue(current)
        else:
            # Unknown total: keep the marquee animation but still update the label.
            self.progress.setRange(0, 0)
        if message:
            self.progress_label.setText(message)

    def _reset_progress(self) -> None:
        self.progress.setRange(0, 0)
        self.progress.reset()
        self.progress_label.setText("")

    def _on_upload_done(self, sid: str) -> None:
        self._append_log(f"[done] server session ready: {sid}")
        self.progress.hide()
        self.progress_label.hide()
        self.run_btn.setEnabled(True); self.back_btn.setEnabled(True)
        self.next_btn.setEnabled(True)

    def _on_failed(self, msg: str) -> None:
        self._append_log(f"[ERROR] {msg}")
        self.progress.hide()
        self.progress_label.hide()
        self.run_btn.setEnabled(True); self.back_btn.setEnabled(True)
