import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from .rag.embedder import embed_text
from .schemas import Contact, ContactCreate, ContactPatch

# Zorg dat er in het project een map bestaat waar je Qdrant-data
# aan kunt koppelen via Docker (-v ...:/qdrant/storage).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
QDRANT_LOCAL_DIR = _PROJECT_ROOT / "qdrant_storage"
QDRANT_LOCAL_DIR.mkdir(parents=True, exist_ok=True)


def _get_qdrant_client(embedded_path: Optional[Path] = None) -> QdrantClient:
    """Initialise a Qdrant client.

    - Zonder QDRANT_HOST: gebruik embedded Qdrant met opslag in qdrant_storage/.
    - Met QDRANT_HOST: verbind naar een externe Qdrant-server (bijv. Docker).
    """

    host = os.getenv("QDRANT_HOST")
    if not host:
        if embedded_path is None:
            env_path = os.getenv("QDRANT_EMBEDDED_PATH")
            db_path = Path(env_path) if env_path else QDRANT_LOCAL_DIR / "contacts_db"
        else:
            db_path = embedded_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return QdrantClient(path=str(db_path))

    port = int(os.getenv("QDRANT_PORT", "6333"))
    api_key = os.getenv("QDRANT_API_KEY") or None
    return QdrantClient(host=host, port=port, api_key=api_key)


class ContactsRepository:
    """Persist contacts in a Qdrant collection with vector embeddings."""

    def __init__(self) -> None:
        self.collection = os.getenv("QDRANT_CONTACTS_COLLECTION", "contacten")
        env_path = os.getenv("QDRANT_EMBEDDED_PATH")
        self._embedded_path = (
            Path(env_path) if env_path else QDRANT_LOCAL_DIR / "contacts_db"
        )
        self._client: Optional[QdrantClient] = None

    def _client_instance(self) -> QdrantClient:
        if self._client is None:
            self._client = _get_qdrant_client(self._embedded_path)
        return self._client

    def _ensure_collection(self, vector_size: int) -> None:
        """Zorg dat de collectie bestaat."""

        client = self._client_instance()
        try:
            client.get_collection(self.collection)
        except Exception:
            client.recreate_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )

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
        client = self._client_instance()
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
        self._ensure_collection(len(vector))

        client = self._client_instance()
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
        client = self._client_instance()
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
        self._ensure_collection(len(vector))

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

    def search_contacts(self, query: str, limit: int = 3) -> list[tuple[Contact, float]]:
        """Zoek naar contacten die qua embedding het dichtst bij *query* liggen."""

        vector = embed_text(query).vector
        client = self._client_instance()
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
