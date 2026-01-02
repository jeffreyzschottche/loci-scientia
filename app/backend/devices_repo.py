import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

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

from .contacts_repo import _get_qdrant_client, QDRANT_LOCAL_DIR
from .rag.embedder import embed_text
from .schemas import Device, DeviceCreate, DevicePatch


class DevicesRepository:
    """Persist devices in a Qdrant collection with simple vectors."""

    def __init__(self) -> None:
        self.collection = os.getenv("QDRANT_DEVICES_COLLECTION", "devices")
        env_path = os.getenv("QDRANT_DEVICES_EMBEDDED_PATH")
        self._embedded_path = (
            Path(env_path).expanduser() if env_path else QDRANT_LOCAL_DIR / "devices_db"
        )

    def _client_context(self):
        return _get_qdrant_client(self._embedded_path)

    def _embedding_text(self, payload: Dict[str, str]) -> str:
        parts = []
        for key in ("device_name", "user_name", "email", "phone"):
            value = payload.get(key)
            if value:
                parts.append(value)
        return " ".join(parts)

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
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            # HNSW index voor snellere similarity search
            hnsw_config=HnswConfigDiff(
                m=16,                # Aantal edges per node
                ef_construct=100,    # Nauwkeurigheid bij index opbouw
            ),
            # Scalar quantization: float32 → int8 (75% minder geheugen)
            quantization_config=ScalarQuantization(
                scalar=ScalarQuantizationConfig(
                    type=ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True,
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
            text = self._embedding_text(payload)
            vector = list(embed_text(text).vector)
            new_points.append(PointStruct(id=payload["id"], vector=vector, payload=payload))
        client.upsert(collection_name=self.collection, points=new_points)

    def _ensure_collection(self, client: QdrantClient, vector_size: int) -> None:
        try:
            info = client.get_collection(self.collection)
        except Exception:
            self._create_collection(client, vector_size)
            return

        current_size = self._collection_vector_size(info)
        if current_size == vector_size:
            return
        self._rebuild_collection(client, vector_size)

    def _device_from_payload(self, payload: Dict, fallback_id: Optional[str] = None) -> Device:
        payload = dict(payload)
        payload.setdefault("id", fallback_id or uuid.uuid4().hex)
        return Device(
            id=str(payload["id"]),
            user_name=payload.get("user_name", ""),
            email=payload.get("email", ""),
            password=payload.get("password", ""),
            phone=payload.get("phone", ""),
            device_name=payload.get("device_name", ""),
        )

    def list_devices(self) -> List[Device]:
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

        devices: List[Device] = []
        for point in points:
            payload = point.payload or {}
            try:
                devices.append(self._device_from_payload(payload, fallback_id=str(point.id)))
            except KeyError:
                continue
        return devices

    def create_device(self, data: DeviceCreate) -> Device:
        did = uuid.uuid4().hex
        payload = {
            "id": did,
            "user_name": data.user_name,
            "email": data.email,
            "password": data.password,
            "phone": data.phone,
            "device_name": data.device_name,
        }

        text = self._embedding_text(payload)
        vector = list(embed_text(text).vector)

        with self._client_context() as client:
            self._ensure_collection(client, len(vector))
            client.upsert(
                collection_name=self.collection,
                points=[
                    PointStruct(
                        id=did,
                        vector=vector,
                        payload=payload,
                    )
                ],
            )

        return self._device_from_payload(payload)

    def update_device(self, device_id: str, patch: DevicePatch) -> Device:
        with self._client_context() as client:
            existing = client.retrieve(
                collection_name=self.collection,
                ids=[device_id],
                with_payload=True,
                with_vectors=False,
            )
        if not existing:
            raise ValueError("device not found")

        payload = dict(existing[0].payload or {})
        payload.setdefault("id", device_id)
        payload.update(patch.model_dump(exclude_unset=True))

        text = self._embedding_text(payload)
        vector = list(embed_text(text).vector)

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

        return self._device_from_payload(payload)

    def delete_device(self, device_id: str) -> None:
        with self._client_context() as client:
            client.delete(collection_name=self.collection, points_selector=[device_id])

    def search_devices(self, query: str, limit: int = 3) -> list[tuple[Device, float]]:
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
        matches: list[tuple[Device, float]] = []
        for hit in response.points:
            payload = hit.payload or {}
            try:
                device = self._device_from_payload(payload, fallback_id=str(hit.id))
            except KeyError:
                continue
            score = hit.score or 0.0
            matches.append((device, score))
        return matches
