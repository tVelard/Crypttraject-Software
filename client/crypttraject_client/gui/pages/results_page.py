"""Page 4 — show clusters, allow export."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..state import AppState


class ResultsPage(QWidget):
    restart_requested = Signal()

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.addWidget(QLabel("<h2>Step 4 — Results</h2>"))

        self.summary = QLabel("")
        root.addWidget(self.summary)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Cluster id", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        footer = QHBoxLayout()
        export = QPushButton("Export clusters as JSON…")
        export.clicked.connect(self._export)
        footer.addWidget(export)
        footer.addStretch(1)
        restart = QPushButton("Start over")
        restart.clicked.connect(self.restart_requested.emit)
        footer.addWidget(restart)
        root.addLayout(footer)

    def on_show(self) -> None:
        clusters = self.state.clusters
        n_records = len(clusters)
        n_clusters = len(set(clusters.values()))
        self.summary.setText(
            f"<b>{n_records}</b> records grouped into <b>{n_clusters}</b> clusters "
            f"(threshold = {self.state.threshold:.2f})."
        )
        counts = Counter(clusters.values())
        self.table.setRowCount(len(counts))
        for row, (cid, n) in enumerate(sorted(counts.items())):
            self.table.setItem(row, 0, QTableWidgetItem(str(cid)))
            self.table.setItem(row, 1, QTableWidgetItem(str(n)))

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export clusters", "clusters.json", "JSON (*.json)")
        if not path:
            return
        payload = {
            "n_clusters": len(set(self.state.clusters.values())),
            "threshold": self.state.threshold,
            "clusters": self.state.clusters,
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
