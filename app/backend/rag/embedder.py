"""Embedding helper dat fastembed gebruikt en dus afgesneden kan draaien."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional, Sequence

import os
import shutil

from fastembed import TextEmbedding

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "fastembed"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_MODEL_ROOT = _PROJECT_ROOT / "fastembed_models"
LOCAL_MODEL_ROOT.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class EmbeddingResult:
    text: str
    vector: Sequence[float]

    @property
    def dimension(self) -> int:
        return len(self.vector)


def _cache_dir() -> Path:
    """Bepaal waar fastembed de modellen mag cachen."""
    override = os.getenv("FASTEMBED_CACHE_DIR")
    if override:
        path = Path(override).expanduser()
    else:
        path = DEFAULT_CACHE_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_model_dir_name(model_name: str) -> str:
    return model_name.replace("/", "__")


def _local_model_dir(model_name: str) -> Path:
    override = os.getenv("FASTEMBED_MODEL_DIR")
    if override:
        return Path(override).expanduser()
    return LOCAL_MODEL_ROOT / _safe_model_dir_name(model_name)


def _allow_download() -> bool:
    flag = os.getenv("FASTEMBED_ALLOW_DOWNLOAD", "")
    return flag.strip().lower() in {"1", "true", "yes", "on"}


def _seed_local_model(embedder: TextEmbedding, target_dir: Path) -> None:
    """Kopieer een gedownloade fastembed map naar het project voor offline gebruik."""
    try:
        model_dir = Path(getattr(embedder.model, "_model_dir"))
    except Exception:
        return
    if not model_dir.exists() or target_dir.exists():
        return
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(model_dir, target_dir)
    except FileExistsError:
        pass


@lru_cache(maxsize=None)
def _model_metadata(model_name: str) -> dict:
    for model in TextEmbedding.list_supported_models():
        if model_name.lower() == model["model"].lower():
            return model
    raise ValueError(f"Onbekend fastembed model: {model_name}")


def _snapshot_dir_from_cache(cache_dir: Path, model_name: str) -> Optional[Path]:
    meta = _model_metadata(model_name)
    sources = meta.get("sources") or {}
    hf_repo = sources.get("hf")
    if not hf_repo:
        return None
    repo_dir = cache_dir / f"models--{hf_repo.replace('/', '--')}"
    snapshots_dir = repo_dir / "snapshots"
    if not snapshots_dir.exists():
        return None
    candidates = sorted(
        [path for path in snapshots_dir.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for snapshot in candidates:
        if any(snapshot.iterdir()):
            return snapshot
    return None


def _try_seed_from_cache(cache_dir: Path, local_dir: Path, model_name: str) -> None:
    if local_dir.exists():
        return
    snapshot = _snapshot_dir_from_cache(cache_dir, model_name)
    if not snapshot or not snapshot.exists():
        return
    local_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(snapshot, local_dir)
    except FileExistsError:
        pass


def _is_model_complete(model_dir: Path) -> bool:
    """Check of het model compleet is door te kijken of de essentiële bestanden bestaan."""
    if not model_dir.exists():
        return False
    # Check voor de ONNX model bestanden
    required_files = ["model_optimized.onnx", "config.json"]
    for filename in required_files:
        if not (model_dir / filename).exists():
            return False
    return True


@lru_cache(maxsize=1)
def _text_embedder() -> TextEmbedding:
    """Cache de fastembed instantie zodat modellen één keer worden geladen."""
    model_name = os.getenv("FASTEMBED_MODEL", DEFAULT_MODEL)
    cache_dir = _cache_dir()
    local_dir = _local_model_dir(model_name)
    _try_seed_from_cache(cache_dir, local_dir, model_name)
    if _is_model_complete(local_dir):
        return TextEmbedding(
            model_name=model_name,
            cache_dir=str(cache_dir),
            local_files_only=True,
            specific_model_path=str(local_dir),
        )
    if not _allow_download():
        raise RuntimeError(
            (
                f"Fastembed model '{model_name}' ontbreekt lokaal in {local_dir}. "
                "Plaats de uitgepakte modelbestanden daar of zet FASTEMBED_ALLOW_DOWNLOAD=1 "
                "om het eenmalig automatisch op te halen."
            )
        )
    # Verwijder incomplete model directory als die bestaat
    if local_dir.exists():
        shutil.rmtree(local_dir)
    embedder = TextEmbedding(model_name=model_name, cache_dir=str(cache_dir))
    _seed_local_model(embedder, local_dir)
    return embedder


def embed_text(text: str) -> EmbeddingResult:
    """Embed de tekst met fastembed en geef de vector terug."""
    embedder = _text_embedder()
    # embed() retourneert een generator, we willen alleen het eerste (en enige) item.
    vector = next(embedder.embed([text]))
    return EmbeddingResult(text=text, vector=vector)
