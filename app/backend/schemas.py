from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 128


class ContactBase(BaseModel):
    name: str
    company: str
    email: str
    phone: str
    notes: str = ""
    location_label: Optional[str] = None
    location_street: Optional[str] = None
    location_city: Optional[str] = None
    location_region: Optional[str] = None
    location_country: Optional[str] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    location_context: Optional[str] = None


class Contact(ContactBase):
    id: str


class ContactCreate(ContactBase):
    pass


class ContactPatch(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    location_label: Optional[str] = None
    location_street: Optional[str] = None
    location_city: Optional[str] = None
    location_region: Optional[str] = None
    location_country: Optional[str] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    location_context: Optional[str] = None


class Device(BaseModel):
    id: str
    user_name: str
    email: str
    password: str
    phone: str
    device_name: str


class DeviceCreate(BaseModel):
    user_name: str
    email: str
    password: str
    phone: str
    device_name: str


class DevicePatch(BaseModel):
    user_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    phone: Optional[str] = None
    device_name: Optional[str] = None


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


class SignOnRequest(BaseModel):
    user_name: str
    password: str


class BearerTokenResponse(BaseModel):
    token: str
    expires_at: datetime


class OllamaModelState(BaseModel):
    current_model: str
    available_models: list[str]


class OllamaModelSwitch(BaseModel):
    model: str
