import os
import uuid
from pathlib import Path
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from .rag.embedder import embed_text
from .schemas import Contact, ContactCreate

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

    def _ensure_collection(self, vector_size: int) -> None:
        """Zorg dat de collectie bestaat.

        We gebruiken een vaste vectorgrootte voor contacten. Als de
        collectie nog niet bestaat, maken we deze aan. We doen verder
        geen automatische migraties; bij schemawijzigingen kun je de
        embedded database-map éénmalig verwijderen.
        """

        client = _get_qdrant_client(self._embedded_path)
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

    def list_contacts(self) -> List[Contact]:
        client = _get_qdrant_client(self._embedded_path)
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
                    Contact(
                        id=str(payload.get("id") or point.id),
                        name=payload["name"],
                        company=payload.get("company", ""),
                        email=payload.get("email", ""),
                        phone=payload.get("phone", ""),
                        notes=payload.get("notes", ""),
                    )
                )
            except KeyError:
                continue
        return contacts

    def create_contact(self, data: ContactCreate) -> Contact:
        # Bouw een beschrijving van het contact op en genereer een
        # embeddingvector via de FastEmbed-pipeline, zodat we later
        # semantische zoekacties kunnen doen over contacten.
        text = "\n".join(
            [
                data.name,
                data.company,
                data.email,
                data.phone,
                data.notes,
            ]
        )
        embedding = embed_text(text)
        vector = list(embedding.vector)
        vector_size = len(vector)
        self._ensure_collection(vector_size)

        cid = uuid.uuid4().hex
        payload = {
            "id": cid,
            "name": data.name,
            "company": data.company,
            "email": data.email,
            "phone": data.phone,
            "notes": data.notes,
        }

        client = _get_qdrant_client(self._embedded_path)
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

        return Contact(id=cid, **data.model_dump())

    def search_contacts(self, query: str, limit: int = 3) -> list[tuple[Contact, float]]:
        """Zoek naar contacten die qua embedding het dichtst bij *query* liggen."""

        vector = embed_text(query).vector
        client = _get_qdrant_client(self._embedded_path)
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
                contact = Contact(
                    id=str(payload.get("id") or hit.id),
                    name=payload["name"],
                    company=payload.get("company", ""),
                    email=payload.get("email", ""),
                    phone=payload.get("phone", ""),
                    notes=payload.get("notes", ""),
                )
            except KeyError:
                continue
            score = hit.score or 0.0
            matches.append((contact, score))

        return matches
