from datetime import datetime, timedelta, timezone
import hashlib
from typing import Optional
from app.models import Project, User, Question


def _now():
    return datetime.now(timezone.utc)


def _age_hours(project: Project) -> float:
    if not project.created_at:
        return 999
    created = project.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    delta = _now() - created
    return delta.total_seconds() / 3600


def calculate_need_score(project: Project) -> int:
    count = project.feedback_count or 0
    if count == 0:
        return 30
    elif count == 1:
        return 20
    elif count == 2:
        return 12
    elif count == 3:
        return 6
    else:
        return 0


def calculate_freshness_score(project: Project) -> int:
    hours = _age_hours(project)
    if hours < 6:
        return 20
    elif hours < 24:
        return 15
    elif hours < 72:
        return 10
    elif hours < 168:
        return 5
    else:
        return 0


def calculate_unseen_score(project: Project, user: Optional[User], recent_viewed_project_ids: set) -> int:
    if user is None:
        return 10
    if project.id in recent_viewed_project_ids:
        return 0
    return 15


def calculate_question_score(project: Project, question_text: Optional[str]) -> int:
    score = 0
    if not question_text:
        return 0
    score += 5
    stripped = question_text.strip()
    if 30 <= len(stripped) <= 200:
        score += 3
    if "?" in stripped:
        score += 2
    generic_questions = ["what do you think", "any feedback", "thoughts?", "how is this", "is this good"]
    lower = stripped.lower()
    if not any(g in lower for g in generic_questions):
        score += 3
    if len(stripped.split()) >= 6:
        score += 2
    return min(score, 15)


def calculate_reciprocity_score(user: Optional[User]) -> int:
    if user is None:
        return 0
    count = user.feedback_given_count or 0
    if count == 0:
        return 0
    elif count == 1:
        return 3
    elif count == 2:
        return 5
    elif 3 <= count <= 5:
        return 7
    else:
        return 10


def calculate_exploration_score(project: Project, user: Optional[User]) -> int:
    user_id = user.id if user else 0
    seed_str = f"{user_id}:{project.id}"
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:8], 16)
    return seed % 11


def calculate_project_score(project, question_text, user, recent_viewed_project_ids):
    need = calculate_need_score(project)
    freshness = calculate_freshness_score(project)
    unseen = calculate_unseen_score(project, user, recent_viewed_project_ids)
    question = calculate_question_score(project, question_text)
    reciprocity = calculate_reciprocity_score(user)
    exploration = calculate_exploration_score(project, user)
    return min(need + freshness + unseen + question + reciprocity + exploration, 100)


def get_match_reason(project, score_components):
    if score_components.get("need", 0) >= 20:
        return "Needs feedback"
    if score_components.get("freshness", 0) >= 15:
        return "New project"
    if score_components.get("unseen", 0) >= 15:
        return "You haven't reviewed this project yet"
    return "Looking for feedback"
