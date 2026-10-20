from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str = "employee"
    created_at: datetime


class CaptchaResponse(BaseModel):
    captcha_id: str
    image_data: str
    expires_in: int
    debug_code: str | None = None


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=72)
    confirm_password: str = Field(min_length=8, max_length=72)
    captcha_id: str
    captcha_code: str = Field(min_length=1, max_length=12)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=72)
    captcha_id: str
    captcha_code: str = Field(min_length=1, max_length=12)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    is_shared: bool = False


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    is_shared: bool | None = None


class KnowledgeBaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    is_shared: bool = False
    is_owner: bool = False
    can_manage: bool = False
    can_view: bool = False
    can_upload: bool = False
    created_at: datetime
    updated_at: datetime


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    knowledge_base_id: int
    filename: str
    file_type: str
    status: str
    chunk_size: int
    overlap: int
    retrieval_mode: str
    char_count: int
    error_message: str | None
    can_manage: bool = True
    created_at: datetime


class ChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    knowledge_base_id: int
    chunk_index: int
    content: str
    metadata_json: dict
    updated_at: datetime


class ChunkUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=20000)


class DocumentDetail(DocumentRead):
    chunks: list[ChunkRead]


class ChatSessionCreate(BaseModel):
    title: str = Field(default="新对话", min_length=1, max_length=128)
    model: str = Field(default="qwen-max", max_length=64)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.8, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, ge=64, le=8192)
    history_turns: int = Field(default=5, ge=0, le=20)


class ChatSessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    model: str | None = Field(default=None, max_length=64)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=64, le=8192)
    history_turns: int | None = Field(default=None, ge=0, le=20)


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    history_turns: int
    created_at: datetime
    updated_at: datetime


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    citations: list
    created_at: datetime


class ChatRequest(BaseModel):
    session_id: int
    question: str = Field(min_length=1, max_length=8000)
    knowledge_base_ids: list[int] = Field(min_length=1)
    model: str | None = Field(default=None, max_length=64)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=64, le=8192)
    history_turns: int | None = Field(default=None, ge=0, le=20)


class Citation(BaseModel):
    index: int
    chunk_id: int
    document_id: int
    document_name: str
    knowledge_base_id: int
    score: float
    snippet: str
class UserAdminRead(UserRead):
    is_active: bool = True


class UserRoleUpdate(BaseModel):
    role: str = Field(pattern=r"^(admin|employee)$")


class KnowledgePermissionRead(BaseModel):
    user_id: int
    username: str
    can_view: bool
    can_upload: bool


class KnowledgePermissionUpdate(BaseModel):
    can_view: bool = False
    can_upload: bool = False
