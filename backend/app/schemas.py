from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    url: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)


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
