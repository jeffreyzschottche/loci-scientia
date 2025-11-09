from typing import Literal, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 128


class ApiRoute(BaseModel):
    id: str
    name: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    path: str
    port: int
    knowledge_base: Optional[str] = None
    api_key: Optional[str] = None
    active: bool = True


class ApiRouteCreate(BaseModel):
    name: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    path: str
    port: int
    knowledge_base: Optional[str] = None
    api_key: Optional[str] = None
    active: bool = True
