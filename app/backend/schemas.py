from datetime import datetime
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str


class PromptDocument(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    filename: str = Field(validation_alias=AliasChoices("filename", "name"))
    data: str = Field(validation_alias=AliasChoices("data", "base64", "content"))
    content_type: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("content_type", "mime_type", "type"),
    )


class ChatRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 128
    history: list[ChatMessage] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    documents: list[PromptDocument] = Field(default_factory=list)
    new_chat: bool = False  # When True, clears server-side chat history first


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


class SignOnRequest(BaseModel):
    user_name: str
    password: str


class BearerTokenResponse(BaseModel):
    token: str
    expires_at: datetime


class OllamaModelRequest(BaseModel):
    model: str


class SupportAccessRequest(BaseModel):
    duration_minutes: int = 60
    public_key: Optional[str] = None
    ticket: Optional[str] = None


class SupportAccessStatus(BaseModel):
    active: bool
    enabled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    session_id: Optional[str] = None
    requested_by: Optional[str] = None
    last_error: Optional[str] = None
