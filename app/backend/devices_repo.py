import os
import uuid
from pathlib import Path
from typing import List

from qdrant_client.models import Distance, PointStruct, VectorParams

from .contacts_repo import _get_qdrant_client, QDRANT_LOCAL_DIR
from .rag.embedder import embed_text
from .schemas import Device, DeviceCreate


class DevicesRepository:
    """Persist devices in a Qdrant collection with simple vectors."""

    def __init__(self) -> None:
        self.collection = os.getenv("QDRANT_DEVICES_COLLECTION", "devices")
        env_path = os.getenv("QDRANT_DEVICES_EMBEDDED_PATH")
        self._embedded_path = (
            Path(env_path) if env_path else QDRANT_LOCAL_DIR / "devices_db"
        )

    def _ensure_collection(self, vector_size: int) -> None:
        client = _get_qdrant_client(self._embedded_path)
        try:
            client.get_collection(self.collection)
        except Exception:
            client.recreate_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def list_devices(self) -> List[Device]:
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

        devices: List[Device] = []
        for point in points:
            payload = point.payload or {}
            try:
                devices.append(
                    Device(
                        id=str(payload.get("id") or point.id),
                        user_name=payload["user_name"],
                        email=payload.get("email", ""),
                        password=payload.get("password", ""),
                        phone=payload.get("phone", ""),
                        device_name=payload.get("device_name", ""),
                    )
                )
            except KeyError:
                continue
        return devices

    def create_device(self, data: DeviceCreate) -> Device:
        text_components = filter(
            None,
            [
                data.device_name,
                data.user_name,
                data.email,
                data.phone,
            ],
        )
        text = " ".join(text_components)
        vector = list(embed_text(text).vector)
        vector_size = len(vector)
        self._ensure_collection(vector_size)

        did = uuid.uuid4().hex
        payload = {
            "id": did,
            "user_name": data.user_name,
            "email": data.email,
            "password": data.password,
            "phone": data.phone,
            "device_name": data.device_name,
        }

        client = _get_qdrant_client(self._embedded_path)
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

        return Device(id=did, **data.model_dump())

    def search_devices(self, query: str, limit: int = 3) -> list[tuple[Device, float]]:
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
        matches: list[tuple[Device, float]] = []
        for hit in response.points:
            payload = hit.payload or {}
            try:
                device = Device(
                    id=str(payload.get("id") or hit.id),
                    user_name=payload["user_name"],
                    email=payload.get("email", ""),
                    password=payload.get("password", ""),
                    phone=payload.get("phone", ""),
                    device_name=payload.get("device_name", ""),
                )
            except KeyError:
                continue
            score = hit.score or 0.0
            matches.append((device, score))
        return matches
