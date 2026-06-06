"""Screen 1 — pick a Geolife .plt directory and the server.

Everything entered here is validated and written into AppState before the
run starts. Nothing is uploaded from this screen: parsing and hashing are
local, and the only thing the server ever receives later is ciphertext.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..state import AppState


class ConfigPage(QWidget):
    run_requested = Signal()

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        root = QVBoxLayout(body)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 8)

        root.addWidget(QLabel(
            "<h2>Configuration</h2>"
            "<p>Pick a Geolife <b>.plt</b> trajectory directory and the server "
            "to use. Parsing and hashing happen <b>locally</b>; the server only "
            "ever sees encrypted signatures.</p>"
        ))

        # --- Source group: a Geolife .plt directory ---
        src_box = QGroupBox("Source — Geolife .plt directory")
        src_form = QFormLayout(src_box)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("…/Geolife Trajectories 1.3/Data")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse)
        src_form.addRow("Directory:", path_row)
        root.addWidget(src_box)

        # --- Feature extraction group (geohash on lat/lon points) ---
        feat_box = QGroupBox("Feature extraction")
        feat_form = QFormLayout(feat_box)
        self.geohash_precision = QSpinBox()
        self.geohash_precision.setRange(1, 12)
        self.geohash_precision.setValue(6)
        feat_form.addRow("Geohash precision:", self.geohash_precision)
        root.addWidget(feat_box)

        # --- Server + clustering group ---
        srv_box = QGroupBox("Server & clustering")
        srv_form = QFormLayout(srv_box)
        self.server_url = QLineEdit(self.state.server_url)
        self.server_url.setPlaceholderText("https://crypttraject.rezel.net/api")
        srv_form.addRow("Server URL:", self.server_url)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.0, 1.0); self.threshold.setSingleStep(0.05)
        self.threshold.setValue(0.5)
        srv_form.addRow("Similarity threshold:", self.threshold)
        self.limit = QSpinBox(); self.limit.setRange(2, 100000); self.limit.setValue(50)
        srv_form.addRow("Max records:", self.limit)
        self.server_timeout = QSpinBox()
        self.server_timeout.setRange(30, 3600); self.server_timeout.setSingleStep(30)
        self.server_timeout.setValue(int(self.state.server_timeout))
        self.server_timeout.setSuffix(" s")
        srv_form.addRow("Server timeout:", self.server_timeout)
        self.num_perm = QSpinBox()
        self.num_perm.setRange(16, 2048); self.num_perm.setSingleStep(16); self.num_perm.setValue(128)
        srv_form.addRow("MinHash permutations:", self.num_perm)
        root.addWidget(srv_box)

        root.addStretch(1)

        # --- Footer (outside the scroll area, always visible) ---
        footer = QHBoxLayout()
        footer.setContentsMargins(16, 4, 16, 12)
        self.error_label = QLabel(""); self.error_label.setStyleSheet("color: #b91c1c;")
        footer.addWidget(self.error_label, 1, Qt.AlignLeft)
        self.run_btn = QPushButton("Lancer le clustering  ▶")
        self.run_btn.setStyleSheet(
            "padding: 8px 18px; font-weight: 600; background: #0d6efd; color: white; border-radius: 6px;"
        )
        self.run_btn.clicked.connect(self._on_run)
        footer.addWidget(self.run_btn)
        outer.addLayout(footer)

    # ------------------------------------------------------------------

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Pick a Geolife .plt directory")
        if path:
            self.path_edit.setText(path)

    # ------------------------------------------------------------------

    def _on_run(self) -> None:
        try:
            self._validate_and_save()
        except ValueError as exc:
            self.error_label.setText(str(exc))
            return
        self.error_label.setText("")
        self.run_requested.emit()

    def _validate_and_save(self) -> None:
        path = self.path_edit.text().strip()
        if not path:
            raise ValueError("Pick a Geolife .plt directory first.")
        p = Path(path)
        if not p.exists():
            raise ValueError(f"Directory does not exist: {p}")
        if not p.is_dir():
            raise ValueError(f"Not a directory: {p}")

        server = self.server_url.text().strip()
        if not server:
            raise ValueError("Enter a server URL.")
        self.state.server_url = server

        self.state.source_path = p
        self.state.geohash_precision = self.geohash_precision.value()
        self.state.threshold = self.threshold.value()
        self.state.limit = self.limit.value()
        self.state.server_timeout = float(self.server_timeout.value())
        self.state.num_perm = self.num_perm.value()
