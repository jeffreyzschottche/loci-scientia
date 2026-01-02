import os
import threading
import uuid
from contextlib import contextmanager, nullcontext
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple, Union

from qdrant_client import QdrantClient
from qdrant_client.models import (
    CollectionInfo,
    Distance,
    HnswConfigDiff,
    PointStruct,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
    VectorParams,
)

from .rag.embedder import embed_text
from .schemas import Contact, ContactCreate, ContactPatch

# Zorg dat er in het project een map bestaat waar je Qdrant-data
# aan kunt koppelen via Docker (-v ...:/qdrant/storage).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
QDRANT_LOCAL_DIR = _PROJECT_ROOT / "qdrant_storage"
QDRANT_LOCAL_DIR.mkdir(parents=True, exist_ok=True)

_QDRANT_EMBED_LOCK = threading.Lock()


def _contacts_embedded_path_from_env() -> Path:
    env_path = os.getenv("QDRANT_CONTACTS_EMBEDDED_PATH") or os.getenv("QDRANT_EMBEDDED_PATH")
    return Path(env_path).expanduser() if env_path else QDRANT_LOCAL_DIR / "contacts_db"


@contextmanager
def _embedded_client_context(path: Path) -> Iterator[QdrantClient]:
    with _QDRANT_EMBED_LOCK:
        client = QdrantClient(path=str(path))
        try:
            yield client
        finally:
            client.close()


@lru_cache(maxsize=None)
def _cached_remote_client(host: str, port: int, api_key: Optional[str]) -> QdrantClient:
    return QdrantClient(host=host, port=port, api_key=api_key or None)


def _qdrant_client_context(embedded_path: Optional[Path] = None):
    """Yield een Qdrant client (embedded of remote) als contextmanager."""

    host = os.getenv("QDRANT_HOST")
    if not host:
        db_path = embedded_path or _contacts_embedded_path_from_env()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return _embedded_client_context(db_path)

    port = int(os.getenv("QDRANT_PORT", "6333"))
    api_key = os.getenv("QDRANT_API_KEY") or None
    return nullcontext(_cached_remote_client(host, port, api_key))


# Backwards compatible alias voor andere modules
_get_qdrant_client = _qdrant_client_context


class ContactsRepository:
    """Persist contacts in a Qdrant collection with vector embeddings."""

    def __init__(self) -> None:
        self.collection = os.getenv("QDRANT_CONTACTS_COLLECTION", "contacten")
        self._embedded_path = _contacts_embedded_path_from_env()

    def _client_context(self):
        return _qdrant_client_context(self._embedded_path)

    def _collection_vector_size(self, info: CollectionInfo) -> Optional[int]:
        vectors = info.config.params.vectors
        if isinstance(vectors, VectorParams):
            return vectors.size
        if isinstance(vectors, dict):
            first = next(iter(vectors.values()), None)
            if isinstance(first, VectorParams):
                return first.size
        return None

    def _iterate_existing_payloads(self, client: QdrantClient) -> List[Tuple[Dict, str]]:
        payloads: List[Tuple[Dict, str]] = []
        next_page: Optional[Union[str, int]] = None
        while True:
            points, next_page = client.scroll(
                collection_name=self.collection,
                with_payload=True,
                with_vectors=False,
                limit=256,
                offset=next_page,
            )
            if not points:
                break
            for point in points:
                payload = dict(point.payload or {})
                fallback_id = str(point.id or uuid.uuid4().hex)
                payloads.append((payload, fallback_id))
            if next_page is None:
                break
        return payloads

    def _create_collection(self, client: QdrantClient, vector_size: int) -> None:
        client.recreate_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
            # HNSW index voor snellere similarity search
            hnsw_config=HnswConfigDiff(
                m=16,                # Aantal edges per node (default 16, hoger = nauwkeuriger maar meer RAM)
                ef_construct=100,    # Nauwkeurigheid bij index opbouw (default 100)
            ),
            # Scalar quantization: float32 → int8 (75% minder geheugen)
            quantization_config=ScalarQuantization(
                scalar=ScalarQuantizationConfig(
                    type=ScalarType.INT8,
                    quantile=0.99,       # Top 1% outliers behouden voor nauwkeurigheid
                    always_ram=True,     # Quantized vectors in RAM voor snelheid
                ),
            ),
            # Payloads op disk opslaan i.p.v. RAM
            on_disk_payload=True,
        )

    def _rebuild_collection(self, client: QdrantClient, vector_size: int) -> None:
        existing_payloads = self._iterate_existing_payloads(client)
        self._create_collection(client, vector_size)
        if not existing_payloads:
            return
        new_points: List[PointStruct] = []
        for payload, fallback_id in existing_payloads:
            payload.setdefault("id", fallback_id)
            vector = list(embed_text(self._embedding_text(payload)).vector)
            new_points.append(
                PointStruct(
                    id=payload["id"],
                    vector=vector,
                    payload=payload,
                )
            )
        client.upsert(collection_name=self.collection, points=new_points)

    def _ensure_collection(self, client: QdrantClient, vector_size: int) -> None:
        """Zorg dat de collectie bestaat en de vector-dimensie klopt."""

        try:
            info = client.get_collection(self.collection)
        except Exception:
            self._create_collection(client, vector_size)
            return

        current_size = self._collection_vector_size(info)
        if current_size == vector_size:
            return
        self._rebuild_collection(client, vector_size)

    def _contact_from_payload(self, payload: Dict, fallback_id: Optional[str] = None) -> Contact:
        return Contact(
            id=str(payload.get("id") or fallback_id or uuid.uuid4().hex),
            name=payload.get("name", ""),
            company=payload.get("company", ""),
            email=payload.get("email", ""),
            phone=payload.get("phone", ""),
            notes=payload.get("notes", ""),
            location_label=payload.get("location_label"),
            location_street=payload.get("location_street"),
            location_city=payload.get("location_city"),
            location_region=payload.get("location_region"),
            location_country=payload.get("location_country"),
            location_lat=payload.get("location_lat"),
            location_lon=payload.get("location_lon"),
            location_context=payload.get("location_context"),
        )

    def _embedding_text(self, payload: Dict) -> str:
        parts: List[str] = []
        for key in (
            "name",
            "company",
            "email",
            "phone",
            "notes",
            "location_label",
            "location_street",
            "location_city",
            "location_region",
            "location_country",
            "location_context",
        ):
            value = payload.get(key)
            if value:
                parts.append(str(value))
        if payload.get("location_lat") is not None and payload.get("location_lon") is not None:
            parts.append(f"{payload['location_lat']}, {payload['location_lon']}")
        return "\n".join(parts)

    def list_contacts(self) -> List[Contact]:
        with self._client_context() as client:
            try:
                points, _ = client.scroll(
                    collection_name=self.collection,
                    limit=1000,
                    with_payload=True,
                    with_vectors=False,
                )
            except Exception:
                return []

        contacts: List[Contact] = []
        for point in points:
            payload = point.payload or {}
            try:
                contacts.append(
                    self._contact_from_payload(payload, fallback_id=str(point.id))
                )
            except KeyError:
                continue
        return contacts

    def create_contact(self, data: ContactCreate) -> Contact:
        payload = data.model_dump()
        cid = uuid.uuid4().hex
        payload["id"] = cid

        embedding = embed_text(self._embedding_text(payload))
        vector = list(embedding.vector)

        with self._client_context() as client:
            self._ensure_collection(client, len(vector))
            client.upsert(
                collection_name=self.collection,
                points=[
                    PointStruct(
                        id=cid,
                        vector=vector,
                        payload=payload,
                    )
                ],
            )

        return self._contact_from_payload(payload)

    def update_contact(self, contact_id: str, patch: ContactPatch) -> Contact:
        with self._client_context() as client:
            existing = client.retrieve(
                collection_name=self.collection,
                ids=[contact_id],
                with_payload=True,
                with_vectors=False,
            )
        if not existing:
            raise ValueError("contact not found")

        payload = existing[0].payload or {}
        payload.setdefault("id", contact_id)

        updates = patch.model_dump(exclude_unset=True)
        payload.update(updates)

        text = self._embedding_text(payload)
        embedding = embed_text(text)
        vector = list(embedding.vector)

        with self._client_context() as client:
            self._ensure_collection(client, len(vector))
            client.upsert(
                collection_name=self.collection,
                points=[
                    PointStruct(
                        id=payload["id"],
                        vector=vector,
                        payload=payload,
                    )
                ],
            )

        return self._contact_from_payload(payload)

    def delete_contact(self, contact_id: str) -> None:
        with self._client_context() as client:
            client.delete(collection_name=self.collection, points_selector=[contact_id])

    def search_contacts(self, query: str, limit: int = 3) -> list[tuple[Contact, float]]:
        """Zoek naar contacten die qua embedding het dichtst bij *query* liggen."""

        vector = embed_text(query).vector
        with self._client_context() as client:
            try:
                response = client.query_points(
                    collection_name=self.collection,
                    query=list(vector),
                    limit=limit,
                    with_payload=True,
                    with_vectors=False,
                )
            except ValueError:
                return []
        matches: list[tuple[Contact, float]] = []
        for hit in response.points:
            payload = hit.payload or {}
            try:
                contact = self._contact_from_payload(payload, fallback_id=str(hit.id))
            except KeyError:
                continue
            score = hit.score or 0.0
            matches.append((contact, score))

        return matches

    def keyword_search_contacts(self, query: str, limit: int = 3) -> list[tuple[Contact, float]]:
        """Fallback voor eenvoudige substring-zoekopdrachten (naam/adres)."""

        needle = query.strip().lower()
        if not needle:
            return []
        contacts = self.list_contacts()
        hits: list[tuple[Contact, float]] = []
        for contact in contacts:
            haystack_parts = [
                contact.name,
                contact.company,
                contact.email,
                contact.phone,
                contact.notes,
                contact.location_label or "",
                contact.location_street or "",
                contact.location_city or "",
                contact.location_region or "",
                contact.location_country or "",
                contact.location_context or "",
            ]
            haystack = " ".join(part for part in haystack_parts if part).lower()
            if needle in haystack:
                hits.append((contact, 1.0))
        return hits[:limit]
