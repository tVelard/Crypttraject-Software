"""Screen 3 — visualise the decrypted clusters.

For geographic sources, each record's trajectory is drawn as a Leaflet
polyline coloured by its cluster, inside a QWebEngineView. For non-geographic
sources (token features), there are no coordinates to plot, so we fall back
to a simple cluster/size table.

Either way, the data shown here was decrypted locally — the server never
saw it in the clear.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    _HAS_WEBENGINE = True
except Exception:   # noqa: BLE001 — QtWebEngine may be missing in dev installs
    _HAS_WEBENGINE = False

from ..state import AppState


# A categorical palette; clusters cycle through it by index.
_PALETTE = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
    "#dcbeff", "#9a6324", "#800000", "#aaffc3", "#808000",
    "#000075", "#a9a9a9", "#ffd8b1", "#000000", "#ffe119",
]


def _color_for(cluster_id: int) -> str:
    return _PALETTE[cluster_id % len(_PALETTE)]


def _build_geojson(
    clusters: Dict[str, int],
    record_points: Dict[str, List[Tuple[float, float]]],
) -> dict:
    """One GeoJSON feature per record carrying points.

    A single point becomes a Point feature; multiple points become a
    LineString (the trajectory). Coordinates are [lon, lat] per GeoJSON.
    """
    features = []
    for rid, pts in record_points.items():
        if not pts:
            continue
        cid = clusters.get(rid, -1)
        coords = [[lon, lat] for (lat, lon) in pts]
        geometry = (
            {"type": "Point", "coordinates": coords[0]}
            if len(coords) == 1
            else {"type": "LineString", "coordinates": coords}
        )
        features.append({
            "type": "Feature",
            "geometry": geometry,
            "properties": {"id": rid, "cluster": cid, "color": _color_for(cid)},
        })
    return {"type": "FeatureCollection", "features": features}


def _map_html(geojson: dict) -> str:
    """A self-contained Leaflet page; Leaflet itself is pulled from a CDN."""
    data = json.dumps(geojson)
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body,#map{height:100%;margin:0;padding:0}
.leaflet-container{background:#f8fafc}</style>
</head><body><div id="map"></div>
<script>
const data = __GEOJSON__;
const map = L.map('map');
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  {maxZoom:19, attribution:'© OpenStreetMap'}).addTo(map);
const layer = L.geoJSON(data, {
  style: f => ({color: f.properties.color, weight: 3, opacity: 0.85}),
  pointToLayer: (f, latlng) => L.circleMarker(latlng,
    {radius:6, color:f.properties.color, fillColor:f.properties.color, fillOpacity:0.8}),
  onEachFeature: (f, l) => l.bindTooltip(
    'id: ' + f.properties.id + '<br>cluster: ' + f.properties.cluster)
}).addTo(map);
try {
  const b = layer.getBounds();
  if (b.isValid()) map.fitBounds(b, {padding:[30,30]});
  else map.setView([20,0], 2);
} catch(e) { map.setView([20,0], 2); }
</script></body></html>""".replace("__GEOJSON__", data)


class MapPage(QWidget):
    restart_requested = Signal()

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(16, 12, 16, 12)

        self.summary = QLabel("")
        self.summary.setStyleSheet("font-size: 14px;")
        root.addWidget(self.summary)

        # Stack: index 0 = map (web view), index 1 = table fallback.
        self.view_stack = QStackedWidget()

        if _HAS_WEBENGINE:
            self.web = QWebEngineView()
            self.view_stack.addWidget(self.web)
        else:
            placeholder = QLabel(
                "QtWebEngine n'est pas disponible dans cet environnement.\n"
                "La carte ne peut pas s'afficher — bascule sur le tableau."
            )
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setWordWrap(True)
            self.web = None
            self.view_stack.addWidget(placeholder)

        # Table fallback
        table_w = QWidget()
        tlay = QVBoxLayout(table_w)
        tlay.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Cluster", "Taille"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        tlay.addWidget(self.table)
        self.view_stack.addWidget(table_w)

        root.addWidget(self.view_stack, 1)

        footer = QHBoxLayout()
        export = QPushButton("Exporter les clusters (JSON)…")
        export.clicked.connect(self._export)
        footer.addWidget(export)
        footer.addStretch(1)
        restart = QPushButton("Nouvelle analyse")
        restart.clicked.connect(self.restart_requested.emit)
        footer.addWidget(restart)
        root.addLayout(footer)

    # ------------------------------------------------------------------

    def on_show(self) -> None:
        clusters = self.state.clusters
        n_records = len(clusters)
        n_clusters = len(set(clusters.values())) if clusters else 0
        self.summary.setText(
            f"<b>{n_records}</b> enregistrements regroupés en "
            f"<b>{n_clusters}</b> clusters (seuil {self.state.threshold:.2f}). "
            "Données déchiffrées localement."
        )

        self._fill_table(clusters)

        if self.state.has_geo() and self.web is not None:
            geojson = _build_geojson(clusters, self.state.record_points)
            self.web.setHtml(_map_html(geojson))
            self.view_stack.setCurrentIndex(0)
        else:
            # No coordinates (or no web engine): show the table fallback.
            self.view_stack.setCurrentIndex(1)

    def _fill_table(self, clusters: Dict[str, int]) -> None:
        counts = Counter(clusters.values())
        self.table.setRowCount(len(counts))
        for row, (cid, n) in enumerate(sorted(counts.items())):
            self.table.setItem(row, 0, QTableWidgetItem(str(cid)))
            self.table.setItem(row, 1, QTableWidgetItem(str(n)))

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Exporter les clusters", "clusters.json", "JSON (*.json)")
        if not path:
            return
        payload = {
            "n_clusters": len(set(self.state.clusters.values())),
            "threshold": self.state.threshold,
            "clusters": self.state.clusters,
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
