import pytest
from datetime import datetime, timedelta, timezone
from app.ranking import (
    calculate_need_score,
    calculate_freshness_score,
    calculate_question_score,
    calculate_reciprocity_score,
    calculate_project_score,
    calculate_exploration_score,
)
from app.models import Project, User


def make_project(feedback_count=0, created_hours_ago=0):
    project = Project(
        title="Test Project",
        description="Test",
        url=None,
        image_url=None,
        owner_id=1,
        feedback_count=feedback_count,
        created_at=datetime.now(timezone.utc) - timedelta(hours=created_hours_ago),
    )
    return project


def make_user(feedback_given_count=0):
    return User(
        github_id=999,
        username="test_user",
        feedback_given_count=feedback_given_count,
    )


class TestNeedScore:
    def test_zero_responses_max_score(self):
        project = make_project(feedback_count=0)
        assert calculate_need_score(project) == 30

    def test_one_response(self):
        project = make_project(feedback_count=1)
        assert calculate_need_score(project) == 20

    def test_four_plus_responses_zero(self):
        project = make_project(feedback_count=4)
        assert calculate_need_score(project) == 0


class TestFreshnessScore:
    def test_under_6_hours(self):
        project = make_project(created_hours_ago=2)
        assert calculate_freshness_score(project) == 20

    def test_week_old_zero(self):
        project = make_project(created_hours_ago=200)
        assert calculate_freshness_score(project) == 0


class TestQuestionScore:
    def test_specific_question_scores_high(self):
        project = make_project()
        score = calculate_question_score(project, "Is it immediately clear what this product does?")
        assert score >= 13

    def test_generic_question_scores_low(self):
        project = make_project()
        score = calculate_question_score(project, "What do you think?")
        assert score < 10

    def test_empty_question_zero(self):
        project = make_project()
        assert calculate_question_score(project, None) == 0


class TestReciprocityScore:
    def test_no_feedback_zero(self):
        user = make_user(feedback_given_count=0)
        assert calculate_reciprocity_score(user) == 0

    def test_six_plus_feedback_max(self):
        user = make_user(feedback_given_count=6)
        assert calculate_reciprocity_score(user) == 10


class TestExplorationScore:
    def test_deterministic(self):
        project = make_project()
        user = make_user()
        s1 = calculate_exploration_score(project, user)
        s2 = calculate_exploration_score(project, user)
        assert s1 == s2
        assert 0 <= s1 <= 10


class TestTotalScore:
    def test_score_in_range(self):
        project = make_project(feedback_count=0, created_hours_ago=1)
        user = make_user(feedback_given_count=2)
        score = calculate_project_score(project, "Is this clear?", user, set())
        assert 0 <= score <= 100

    def test_new_project_scores_high(self):
        project = make_project(feedback_count=0, created_hours_ago=1)
        user = make_user(feedback_given_count=0)
        score = calculate_project_score(project, "Is it clear what this tool does?", user, set())
        assert score >= 70
