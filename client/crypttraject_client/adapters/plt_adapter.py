"""Geolife .plt adapter — kept for backwards compatibility with Old/."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from .base import DataSourceAdapter, Record


@dataclass
class PLTGeolifeAdapter(DataSourceAdapter):
    dataset_dir: Path
    limit: Optional[int] = None
    header_lines: int = 6

    def count(self) -> "int | None":
        if not self.dataset_dir.exists():
            return 0
        # Glob is a single directory listing — cheap even on 10k+ files.
        total = sum(1 for _ in self.dataset_dir.rglob("*.plt"))
        if self.limit is not None:
            return min(total, self.limit)
        return total

    def iter_records(self) -> Iterator[Record]:
        if not self.dataset_dir.exists():
            raise FileNotFoundError(self.dataset_dir)

        count = 0
        for plt_file in sorted(self.dataset_dir.rglob("*.plt")):
            if self.limit is not None and count >= self.limit:
                return
            user_id = plt_file.parts[-3]
            traj_id = f"{user_id}/{plt_file.stem}"
            points = []
            with open(plt_file) as fh:
                for i, line in enumerate(fh):
                    if i < self.header_lines:
                        continue
                    parts = line.split(",")
                    try:
                        points.append((float(parts[0]), float(parts[1])))
                    except (ValueError, IndexError):
                        pass
            if points:
                yield Record(record_id=traj_id, payload={"points": points})
                count += 1
