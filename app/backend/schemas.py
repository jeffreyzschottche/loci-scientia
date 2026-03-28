from datetime import datetime
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str
    images: list[str] = Field(default_factory=list)


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
    request_id: Optional[str] = None
    conversation_id: Optional[str] = None
    mode: Optional[str] = None
    thinking: bool = True
    max_new_tokens: int = 128
    history: list[ChatMessage] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    documents: list[PromptDocument] = Field(default_factory=list)
    new_chat: bool = False  # When True, clears server-side chat history first


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


class ChatCancelRequest(BaseModel):
    request_id: str


class ChatResetRequest(BaseModel):
    conversation_id: Optional[str] = None


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
