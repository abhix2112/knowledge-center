"""Pydantic models: the shapes of API requests and responses.

Like TypeScript interfaces, except they also validate data at runtime.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Status = Literal["draft", "published", "retired"]
Visibility = Literal["private", "public"]


class Input(BaseModel):
    """Base for request bodies: trims spaces around every string."""

    model_config = ConfigDict(str_strip_whitespace=True)


# ---------- Users ----------


class UserCreate(Input):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Articles ----------


class ArticleCreate(Input):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    category: str = Field(default="General", min_length=1, max_length=50)
    tags: list[str] = Field(default_factory=list, max_length=10)
    visibility: Visibility = "public"


class ArticleUpdate(Input):
    """Every field is optional: only the fields you send are changed."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    tags: list[str] | None = Field(default=None, max_length=10)
    visibility: Visibility | None = None


class ArticleSummary(BaseModel):
    """An article without its body, for lists."""

    id: UUID
    number: str
    title: str
    excerpt: str
    category: str
    tags: list[str]
    status: Status
    visibility: Visibility
    source: str
    owner_id: UUID
    owner_name: str
    current_version: int
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ArticleOut(ArticleSummary):
    body: str


class ArticleList(BaseModel):
    items: list[ArticleSummary]
    total: int
    limit: int
    offset: int


class CategoryCount(BaseModel):
    category: str
    count: int


class VersionSummary(BaseModel):
    version: int
    title: str
    created_by_name: str
    created_at: datetime


class VersionOut(VersionSummary):
    body: str


# ---------- Documents ----------


class DocumentOut(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    article_id: UUID | None
    created_at: datetime


class UploadResult(BaseModel):
    document: DocumentOut
    article: ArticleOut
