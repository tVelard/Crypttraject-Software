"""Screen 1 — pick a data source, format, and server settings."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
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

from ...adapters import (
    EXTRACTOR_SPECS,
    SOURCE_SPECS,
    default_extractor_for,
    detect_source,
    validate_source_path,
)
from ..state import AppState


class ConfigPage(QWidget):
    run_requested = Signal()

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._source_manual = False
        self._extractor_manual = False
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
            "<p>Choose a trajectory data source (file or folder). The format is "
            "<b>auto-detected</b> but can be overridden. Parsing and hashing happen "
            "<b>locally</b>; the server only ever sees encrypted signatures.</p>"
        ))

        # --- Source group ---
        src_box = QGroupBox("Data source")
        src_form = QFormLayout(src_box)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("File or folder (Geolife, GPX, CSV, GeoJSON)")
        self.path_edit.textChanged.connect(self._on_path_changed)
        browse_file = QPushButton("File…")
        browse_file.clicked.connect(self._browse_file)
        browse_dir = QPushButton("Folder…")
        browse_dir.clicked.connect(self._browse_dir)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse_file)
        path_row.addWidget(browse_dir)
        src_form.addRow("Path:", path_row)

        self.source_combo = QComboBox()
        for sid, spec in SOURCE_SPECS.items():
            self.source_combo.addItem(spec.label, sid)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        src_form.addRow("Format:", self.source_combo)

        self.source_hint = QLabel("")
        self.source_hint.setWordWrap(True)
        self.source_hint.setStyleSheet("color: #64748b; font-size: 12px;")
        src_form.addRow("", self.source_hint)

        root.addWidget(src_box)

        # --- Feature extraction group ---
        feat_box = QGroupBox("Feature extraction")
        feat_form = QFormLayout(feat_box)

        self.extractor_combo = QComboBox()
        for eid, spec in EXTRACTOR_SPECS.items():
            self.extractor_combo.addItem(spec.label, eid)
        self.extractor_combo.currentIndexChanged.connect(self._on_extractor_changed)
        feat_form.addRow("Method:", self.extractor_combo)

        self.extractor_hint = QLabel("")
        self.extractor_hint.setWordWrap(True)
        self.extractor_hint.setStyleSheet("color: #64748b; font-size: 12px;")
        feat_form.addRow("", self.extractor_hint)

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
        self.threshold.setRange(0.0, 1.0)
        self.threshold.setSingleStep(0.05)
        self.threshold.setValue(0.5)
        srv_form.addRow("Similarity threshold:", self.threshold)
        self.limit = QSpinBox()
        self.limit.setRange(2, 100000)
        self.limit.setValue(50)
        srv_form.addRow("Max records:", self.limit)
        self.server_timeout = QSpinBox()
        self.server_timeout.setRange(30, 3600)
        self.server_timeout.setSingleStep(30)
        self.server_timeout.setValue(int(self.state.server_timeout))
        self.server_timeout.setSuffix(" s")
        srv_form.addRow("Server timeout:", self.server_timeout)
        self.num_perm = QSpinBox()
        self.num_perm.setRange(16, 2048)
        self.num_perm.setSingleStep(16)
        self.num_perm.setValue(128)
        srv_form.addRow("MinHash permutations:", self.num_perm)
        root.addWidget(srv_box)

        root.addStretch(1)

        footer = QHBoxLayout()
        footer.setContentsMargins(16, 4, 16, 12)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b91c1c;")
        footer.addWidget(self.error_label, 1, Qt.AlignLeft)
        self.run_btn = QPushButton("Lancer le clustering  ▶")
        self.run_btn.setStyleSheet(
            "padding: 8px 18px; font-weight: 600; background: #0d6efd; color: white; border-radius: 6px;"
        )
        self.run_btn.clicked.connect(self._on_run)
        footer.addWidget(self.run_btn)
        outer.addLayout(footer)

        self._refresh_hints()
        self._sync_combos_from_state()

    # ------------------------------------------------------------------

    def _combo_id(self, combo: QComboBox) -> str:
        return combo.currentData()

    def _set_combo_by_id(self, combo: QComboBox, item_id: str) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == item_id:
                combo.blockSignals(True)
                combo.setCurrentIndex(i)
                combo.blockSignals(False)
                return

    def _sync_combos_from_state(self) -> None:
        self._set_combo_by_id(self.source_combo, self.state.source_adapter_id)
        self._set_combo_by_id(self.extractor_combo, self.state.extractor_id)

    def _refresh_hints(self) -> None:
        src = SOURCE_SPECS.get(self._combo_id(self.source_combo))
        ext = EXTRACTOR_SPECS.get(self._combo_id(self.extractor_combo))
        self.source_hint.setText(src.description if src else "")
        self.extractor_hint.setText(ext.description if ext else "")

    def _apply_detected_format(self, path: Path) -> None:
        detected = detect_source(path)
        self._set_combo_by_id(self.source_combo, detected)
        if not self._extractor_manual:
            self._set_combo_by_id(
                self.extractor_combo,
                default_extractor_for(detected),
            )
        self._refresh_hints()

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Pick a trajectory file",
            "",
            "Trajectory files (*.plt *.gpx *.csv *.geojson *.json);;All files (*)",
        )
        if path:
            self._source_manual = False
            self._extractor_manual = False
            self.path_edit.setText(path)

    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Pick a trajectory folder")
        if path:
            self._source_manual = False
            self._extractor_manual = False
            self.path_edit.setText(path)

    def _on_path_changed(self, text: str) -> None:
        stripped = text.strip()
        if not stripped:
            return
        path = Path(stripped)
        if not path.exists():
            return
        if not self._source_manual:
            self._apply_detected_format(path)

    def _on_source_changed(self, _index: int) -> None:
        self._source_manual = True
        self._refresh_hints()
        if not self._extractor_manual:
            src_id = self._combo_id(self.source_combo)
            self._set_combo_by_id(
                self.extractor_combo,
                default_extractor_for(src_id),
            )
            self._refresh_hints()

    def _on_extractor_changed(self, _index: int) -> None:
        self._extractor_manual = True
        self._refresh_hints()

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
            raise ValueError("Pick a trajectory file or folder first.")
        p = Path(path)
        source_id = self._combo_id(self.source_combo)
        extractor_id = self._combo_id(self.extractor_combo)
        validate_source_path(source_id, p)

        server = self.server_url.text().strip()
        if not server:
            raise ValueError("Enter a server URL.")

        self.state.server_url = server
        self.state.source_path = p
        self.state.source_adapter_id = source_id
        self.state.extractor_id = extractor_id
        self.state.geohash_precision = self.geohash_precision.value()
        self.state.threshold = self.threshold.value()
        self.state.limit = self.limit.value()
        self.state.server_timeout = float(self.server_timeout.value())
        self.state.num_perm = self.num_perm.value()
