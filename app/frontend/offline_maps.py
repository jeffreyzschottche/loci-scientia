"""Offline map metadata and helper utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    from pmtiles.reader import Reader, MmapSource  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Reader = None  # type: ignore
    MmapSource = None  # type: ignore


@dataclass(frozen=True)
class OfflineRegion:
    country: str
    file_name: str
    size_hint: str
    description: str
    download_url: str


@dataclass
class RegionStatus:
    region: OfflineRegion
    path: Path
    installed: bool
    size_label: str
    valid: bool
    metadata: Optional[Dict]
    error: Optional[str]

    @property
    def country(self) -> str:
        return self.region.country

    @property
    def instructions(self) -> str:
        base = f"Plaats {self.region.file_name} in {self.path.parent}"
        if self.installed:
            return f"Offline map aanwezig in {self.path}"
        return f"Niet gevonden. Download via {self.region.download_url} en {base}."


class OfflineMapManager:
    """Tracks offline PMTiles files for the desktop app."""

    DEFAULT_REGIONS = (
        OfflineRegion(
            country="Nederland",
            file_name="netherlands.pmtiles",
            size_hint="~1.6 GB",
            description="Vector tileset (PMTiles) voor Nederlandse kaart.",
            download_url="https://protomaps-data.nyc3.digitaloceanspaces.com/countries/netherlands.pmtiles",
        ),
        OfflineRegion(
            country="Duitsland",
            file_name="germany.pmtiles",
            size_hint="~4.5 GB",
            description="Vector tileset (PMTiles) voor Duitsland inclusief steden en POI's.",
            download_url="https://protomaps-data.nyc3.digitaloceanspaces.com/countries/germany.pmtiles",
        ),
    )

    def __init__(self, base_dir: Optional[Path] = None, regions: Optional[Iterable[OfflineRegion]] = None):
        default_base = Path(__file__).resolve().parents[2] / "LociMaps" / "offline"
        self.base_dir = Path(base_dir or default_base)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._regions: Dict[str, OfflineRegion] = {
            r.country: r for r in (regions or self.DEFAULT_REGIONS)
        }

    def available_countries(self) -> List[str]:
        return list(self._regions.keys())

    def list_statuses(self) -> List[RegionStatus]:
        return [self.region_status(country) for country in self._regions]

    def region_status(self, country: str) -> RegionStatus:
        region = self._regions[country]
        path = self.base_dir / region.file_name
        installed = path.exists()
        size_label = region.size_hint
        valid = False
        metadata: Optional[Dict] = None
        error: Optional[str] = None
        if installed:
            try:
                size_label = _human_size(path.stat().st_size)
            except OSError:
                pass
            if Reader is None:
                error = "pmtiles pakket niet beschikbaar"
            else:
                try:
                    with path.open("rb") as fh:
                        reader = Reader(MmapSource(fh))  # type: ignore[arg-type]
                        reader.header()
                        metadata = reader.metadata()
                        valid = True
                except Exception as exc:  # pragma: no cover - runtime validation
                    error = str(exc)
        return RegionStatus(
            region=region,
            path=path,
            installed=installed,
            size_label=size_label,
            valid=valid,
            metadata=metadata,
            error=error,
        )

    def download_hint(self, country: str) -> str:
        status = self.region_status(country)
        return (
            f"curl -L {status.region.download_url} -o {status.path}"
            if not status.installed
            else f"Bestand gevonden: {status.path}"
        )


def _human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
