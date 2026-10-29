"""Whitespace-only titles and questions are rejected at the schema boundary.

``min_length=1`` counts the raw string, so ``"   "`` used to pass for both
``ProjectCreate.title`` and ``QuestionCreate.text``. The frontend trims before
posting, but the documented public API accepted blank projects and questions
from any script. ``url``/``image_url`` already established the strip-and-check
pattern in the same file.
"""

import pytest
from pydantic import ValidationError

from app.database import SessionLocal
from app.models import Project, Question, Response
from app.schemas import ProjectCreate, QuestionCreate


def _payload(title="Akiya Scout", text="Understand this page?"):
    return {
        "project_data": {
            "title": title,
            "description": None,
            "url": None,
            "image_url": None,
        },
        "question_data": {"text": text},
    }


def _cleanup_database():
    db = SessionLocal()
    try:
        db.query(Response).delete()
        db.query(Question).delete()
        db.query(Project).delete()
        db.commit()
    finally:
        db.close()


def test_schemas_strip_ordinary_values():
    assert ProjectCreate(title="  Akiya Scout  ").title == "Akiya Scout"
    assert QuestionCreate(text="  Understand this page?  ").text == "Understand this page?"


@pytest.mark.parametrize("title", ["", "   ", "\t\n "])
def test_project_create_rejects_whitespace_only_title(title):
    with pytest.raises(ValidationError):
        ProjectCreate(title=title)


@pytest.mark.parametrize("text", ["", "   ", "\t\n "])
def test_question_create_rejects_whitespace_only_text(text):
    with pytest.raises(ValidationError):
        QuestionCreate(text=text)


@pytest.mark.parametrize(
    "payload",
    [
        _payload(title="   "),
        _payload(title="\t\n"),
        _payload(text=" \t "),
    ],
)
def test_api_rejects_whitespace_only_fields(auth_client, payload):
    response = auth_client.post("/api/projects/", json=payload)
    assert response.status_code == 422


def test_api_creates_a_trimmed_project(auth_client):
    _cleanup_database()

    response = auth_client.post("/api/projects/", json=_payload(title="  Akiya Scout  "))

    assert response.status_code == 201
    data = response.json()
    assert data["project"]["title"] == "Akiya Scout"
    assert data["question"]["text"] == "Understand this page?"
