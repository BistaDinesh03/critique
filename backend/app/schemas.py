from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    url: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)


class ProjectOut(BaseModel):
    """Schema for returning project data."""
    id: int
    title: str
    description: Optional[str]
    url: Optional[str]
    image_url: Optional[str]
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectListItem(BaseModel):
    """Schema for project in discovery list."""
    id: int
    title: str
    description: Optional[str]
    url: Optional[str]
    image_url: Optional[str]
    owner_id: int
    created_at: datetime
    question_text: Optional[str] = None
    response_count: int = 0

    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    """Schema for creating a new question."""
    text: str = Field(..., min_length=1, max_length=500)


class QuestionOut(BaseModel):
    """Schema for returning question data."""
    id: int
    text: str
    is_active: bool
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True


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
