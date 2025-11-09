import uuid
from typing import Dict, List

from .schemas import ApiRoute, ApiRouteCreate


class Store:
    def __init__(self):
        self.routes: Dict[str, ApiRoute] = {}
        # seed sample routes for mock UI
        self.create(
            ApiRouteCreate(
                name="Chat Endpoint",
                method="POST",
                path="/api/chat",
                port=8080,
                knowledge_base="Algemene Kennisbank",
                api_key="loci_sk_1a2b3c4d5e6f",
                active=True,
            )
        )
        self.create(
            ApiRouteCreate(
                name="Knowledge Query",
                method="GET",
                path="/api/knowledge",
                port=8080,
                knowledge_base="Technische Documenten",
                api_key="loci_sk_7g8h9i0j1k2l",
                active=True,
            )
        )

    def list(self) -> List[ApiRoute]:
        return list(self.routes.values())

    def get(self, rid: str) -> ApiRoute:
        return self.routes[rid]

    def create(self, data: ApiRouteCreate) -> ApiRoute:
        rid = uuid.uuid4().hex[:8]
        route = ApiRoute(id=rid, **data.model_dump())
        self.routes[rid] = route
        return route

    def update(self, rid: str, patch: dict) -> ApiRoute:
        route = self.routes[rid]
        updated = route.model_copy(update=patch)
        self.routes[rid] = updated
        return updated

    def delete(self, rid: str) -> None:
        self.routes.pop(rid, None)
