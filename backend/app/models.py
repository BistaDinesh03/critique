from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(Integer, unique=True, nullable=True)  # nullable for non-GitHub users
    username = Column(String(100), unique=True, nullable=False)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="projects")
    questions = relationship("Question", back_populates="project", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Foreign keys
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="questions")
    responses = relationship("Response", back_populates="question", cascade="all, delete-orphan")


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    clarity = Column(String(20), nullable=False)
    would_use = Column(String(10), nullable=False)
    suggestion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Foreign keys
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ip_hash = Column(String(64), nullable=False)

    # Relationships
    question = relationship("Question", back_populates="responses")
    user = relationship("User")
