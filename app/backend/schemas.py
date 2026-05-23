from datetime import datetime
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from .user_roles import DEFAULT_ROLES, normalize_roles


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str
    images: list[str] = Field(default_factory=list)
    documents: list["HistoryDocument"] = Field(default_factory=list)


class HistoryDocument(BaseModel):
    filename: str
    file_type: str
    text: str
    source_bytes: int = 0
    truncated: bool = False


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
    thinking: bool = False
    max_new_tokens: int = 128
    history: list[ChatMessage] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    documents: list[PromptDocument] = Field(default_factory=list)
    new_chat: bool = False  # When True, clears server-side chat history first
    web_search: bool = False  # When True, augment prompt with SearXNG results


class Device(BaseModel):
    id: str
    user_name: str
    email: str
    password: str
    phone: str = ""
    device_name: str
    roles: list[str] = Field(default_factory=lambda: list(DEFAULT_ROLES))
    is_connected: bool = False
    last_seen_at: Optional[datetime] = None


class DeviceCreate(BaseModel):
    user_name: str
    email: str
    password: str
    device_name: str
    roles: list[str] = Field(default_factory=lambda: list(DEFAULT_ROLES))

    @model_validator(mode="after")
    def validate_roles(self) -> "DeviceCreate":
        self.roles = normalize_roles(self.roles)
        return self


class DevicePatch(BaseModel):
    user_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    device_name: Optional[str] = None
    roles: Optional[list[str]] = None

    @model_validator(mode="after")
    def validate_roles(self) -> "DevicePatch":
        if self.roles is not None:
            self.roles = normalize_roles(self.roles)
        return self


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


class SupportTunnelRequest(BaseModel):
    action: Literal["open", "close"]
    duration_minutes: Optional[int] = None

    @model_validator(mode="after")
    def validate_action(self) -> "SupportTunnelRequest":
        if self.action == "open" and self.duration_minutes not in {30, 60, 120}:
            raise ValueError("duration_minutes moet 30, 60 of 120 zijn bij action=open.")
        if self.action == "close":
            self.duration_minutes = None
        return self


class SupportTunnelStatus(BaseModel):
    active: bool
    expires_at: Optional[datetime] = None
    port: Optional[int] = None
    error: Optional[str] = None
