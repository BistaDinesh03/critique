from datetime import datetime
from urllib.parse import urlsplit
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional


def strip_optional_text(value: Optional[str]) -> Optional[str]:
    """Trim optional free text and collapse whitespace-only input to None.

    ``max_length`` counts every character, so ``"   "`` is a valid value and
    would be stored verbatim: it renders as a blank description, or as an
    empty blockquote in the owner's results. Collapsing it to ``None`` keeps
    the field optional (and matches what the frontend already sends for an
    empty textarea) instead of rejecting input the visitor never meant to send.
    """
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    url: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Trim and reject whitespace-only titles: min_length counts spaces."""
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty or whitespace")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Trim descriptions; whitespace-only ones are stored as None."""
        return strip_optional_text(v)

    @field_validator("url")
    @classmethod
    def validate_project_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate project URL: requires valid host, http/https, no credentials or control chars."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in v):
            raise ValueError("URL cannot contain whitespace or control characters")
        try:
            parsed = urlsplit(v)
        except Exception:
            raise ValueError("Invalid URL")
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("URL must have http or https scheme and a valid host")
        if parsed.username or parsed.password:
            raise ValueError("URL cannot contain embedded credentials")
        return v

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate screenshot URL: requires valid host, HTTPS (to prevent mixed content), no credentials."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in v):
            raise ValueError("Image URL cannot contain whitespace or control characters")
        try:
            parsed = urlsplit(v)
        except Exception:
            raise ValueError("Invalid image URL")
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Image URL must use https scheme and have a valid host")
        if parsed.username or parsed.password:
            raise ValueError("Image URL cannot contain embedded credentials")
        return v


class ProjectOut(BaseModel):
    """Schema for returning project data."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: Optional[str]
    url: Optional[str]
    image_url: Optional[str]
    owner_id: int
    created_at: datetime


class ProjectListItem(BaseModel):
    """Schema for project in discovery list."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: Optional[str]
    url: Optional[str]
    image_url: Optional[str]
    owner_id: int
    created_at: datetime
    question_text: Optional[str] = None
    response_count: int = 0


class QuestionCreate(BaseModel):
    """Schema for creating a new question."""
    text: str = Field(..., min_length=1, max_length=500)

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Trim and reject whitespace-only text: min_length counts spaces."""
        v = v.strip()
        if not v:
            raise ValueError("Question text cannot be empty or whitespace")
        return v


class QuestionOut(BaseModel):
    """Schema for returning question data."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    is_active: bool
    project_id: int
    created_at: datetime


class ProjectWithQuestion(BaseModel):
    """Schema for returning a project with its active question."""
    project: ProjectOut
    question: Optional[QuestionOut] = None


class PaginatedProjects(BaseModel):
    """Schema for paginated project list."""
    items: list[ProjectListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ResponseCreate(BaseModel):
    """Schema for creating a response."""
    clarity: str = Field(..., pattern="^(very_clear|mostly_clear|confusing)$")
    would_use: str = Field(..., pattern="^(yes|maybe|no)$")
    suggestion: Optional[str] = Field(None, max_length=2000)

    @field_validator("suggestion")
    @classmethod
    def validate_suggestion(cls, v: Optional[str]) -> Optional[str]:
        """Trim suggestions; whitespace-only ones are stored as None."""
        return strip_optional_text(v)


class ResponseOut(BaseModel):
    """Schema for returning response data (public)."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    clarity: str
    would_use: str
    question_id: int
    created_at: datetime


class ResponseOwnerOut(BaseModel):
    """Schema for returning response data to project owner (includes suggestion)."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    clarity: str
    would_use: str
    suggestion: Optional[str]
    question_id: int
    created_at: datetime
