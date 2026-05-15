"""Page 1 — pick a data source and a feature extractor."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..state import AppState


class SourcePage(QWidget):
    next_requested = Signal()

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        root.addWidget(QLabel(
            "<h2>Step 1 — Data source</h2>"
            "<p>Pick where your records live. The client parses them locally; "
            "<b>nothing is uploaded yet</b>.</p>"
        ))

        # --- Source group ---
        src_box = QGroupBox("Source")
        src_form = QFormLayout(src_box)

        self.kind = QComboBox()
        self.kind.addItems(["plt", "csv", "json", "jsonl"])
        self.kind.currentTextChanged.connect(self._on_kind_changed)
        src_form.addRow("Format:", self.kind)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse)
        src_form.addRow("Path:", path_row)

        # Stacked widget for source-specific options
        self.source_stack = QStackedWidget()
        # plt: nothing
        self.source_stack.addWidget(QWidget())
        # csv
        csv_w = QWidget(); csv_f = QFormLayout(csv_w)
        self.csv_id_col = QLineEdit("id")
        self.csv_points = QLineEdit("")
        self.csv_points.setPlaceholderText("e.g. lat,lon (leave empty for flat rows)")
        csv_f.addRow("Id column:", self.csv_id_col)
        csv_f.addRow("Point columns:", self.csv_points)
        self.source_stack.addWidget(csv_w)
        # json / jsonl
        json_w = QWidget(); json_f = QFormLayout(json_w)
        self.json_id_field = QLineEdit("id")
        json_f.addRow("Id field:", self.json_id_field)
        self.source_stack.addWidget(json_w)
        self.source_stack.addWidget(json_w)   # jsonl reuses the same widget

        src_form.addRow("Options:", self.source_stack)
        root.addWidget(src_box)

        # --- Feature extractor group ---
        feat_box = QGroupBox("Feature extraction")
        feat_form = QFormLayout(feat_box)

        self.feature_kind = QComboBox()
        self.feature_kind.addItems(["geohash", "tokens"])
        self.feature_kind.currentTextChanged.connect(self._on_feature_changed)
        feat_form.addRow("Mode:", self.feature_kind)

        self.feat_stack = QStackedWidget()
        # geohash
        gh_w = QWidget(); gh_f = QFormLayout(gh_w)
        self.geohash_precision = QSpinBox()
        self.geohash_precision.setRange(1, 12)
        self.geohash_precision.setValue(6)
        gh_f.addRow("Geohash precision:", self.geohash_precision)
        self.feat_stack.addWidget(gh_w)
        # tokens
        tok_w = QWidget(); tok_f = QFormLayout(tok_w)
        self.text_fields = QLineEdit()
        self.text_fields.setPlaceholderText("comma-separated, e.g. title,tags,description")
        tok_f.addRow("Text fields:", self.text_fields)
        self.feat_stack.addWidget(tok_w)
        feat_form.addRow("Options:", self.feat_stack)
        root.addWidget(feat_box)

        # --- Limits + MinHash params ---
        misc_box = QGroupBox("Limits & MinHash")
        misc_form = QFormLayout(misc_box)
        self.limit = QSpinBox(); self.limit.setRange(2, 100000); self.limit.setValue(50)
        self.num_perm = QSpinBox(); self.num_perm.setRange(16, 2048); self.num_perm.setSingleStep(16); self.num_perm.setValue(128)
        misc_form.addRow("Max records:", self.limit)
        misc_form.addRow("MinHash permutations:", self.num_perm)
        root.addWidget(misc_box)

        # --- Footer ---
        root.addStretch(1)
        footer = QHBoxLayout()
        self.error_label = QLabel(""); self.error_label.setStyleSheet("color: #b91c1c;")
        footer.addWidget(self.error_label, 1, Qt.AlignLeft)
        self.next_btn = QPushButton("Next — Encrypt")
        self.next_btn.clicked.connect(self._on_next)
        footer.addWidget(self.next_btn)
        root.addLayout(footer)

        self._on_kind_changed(self.kind.currentText())
        self._on_feature_changed(self.feature_kind.currentText())

    # ------------------------------------------------------------------

    def _on_kind_changed(self, kind: str) -> None:
        idx = {"plt": 0, "csv": 1, "json": 2, "jsonl": 3}.get(kind, 0)
        self.source_stack.setCurrentIndex(idx)

    def _on_feature_changed(self, kind: str) -> None:
        self.feat_stack.setCurrentIndex(0 if kind == "geohash" else 1)

    def _browse(self) -> None:
        kind = self.kind.currentText()
        if kind == "plt":
            path = QFileDialog.getExistingDirectory(self, "Pick a Geolife .plt directory")
        else:
            patterns = {"csv": "CSV (*.csv)", "json": "JSON (*.json)", "jsonl": "JSON-Lines (*.jsonl *.ndjson)"}
            path, _ = QFileDialog.getOpenFileName(self, "Pick a data file", "", patterns.get(kind, "All (*)"))
        if path:
            self.path_edit.setText(path)

    # ------------------------------------------------------------------

    def _on_next(self) -> None:
        try:
            self._validate_and_save()
        except ValueError as exc:
            self.error_label.setText(str(exc))
            return
        self.error_label.setText("")
        self.next_requested.emit()

    def _validate_and_save(self) -> None:
        path = self.path_edit.text().strip()
        if not path:
            raise ValueError("Pick a source path first.")
        p = Path(path)
        if not p.exists():
            raise ValueError(f"Path does not exist: {p}")

        kind = self.kind.currentText()
        self.state.source_kind = kind
        self.state.source_path = p

        if kind == "csv":
            self.state.id_column = self.csv_id_col.text().strip() or "id"
            pc = self.csv_points.text().strip()
            self.state.point_columns = tuple(c.strip() for c in pc.split(",")) if pc else None
        elif kind in ("json", "jsonl"):
            self.state.id_field = self.json_id_field.text().strip() or "id"

        self.state.feature_kind = self.feature_kind.currentText()
        if self.state.feature_kind == "geohash":
            self.state.geohash_precision = self.geohash_precision.value()
        else:
            fields = [f.strip() for f in self.text_fields.text().split(",") if f.strip()]
            if not fields:
                raise ValueError("Token mode needs at least one text field.")
            self.state.text_fields = fields

        self.state.limit = self.limit.value()
        self.state.num_perm = self.num_perm.value()
