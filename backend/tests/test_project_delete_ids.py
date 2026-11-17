"""Project deletion handles IDs outside the database integer domain."""
import pytest


@pytest.mark.parametrize("project_id", [-(2**63) - 1, 2**63, -(10**30), 10**30])
def test_delete_out_of_range_project_id_returns_not_found(auth_client, project_id):
    response = auth_client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


@pytest.mark.parametrize("project_id", [-(2**63), 2**63 - 1])
def test_delete_missing_boundary_project_id_returns_not_found(auth_client, project_id):
    response = auth_client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_delete_project_cascade_cleanup(auth_client):
    """Deleting a project removes dependent responses, questions, events, and views (fixes #289)."""
    from app.database import SessionLocal
    from app.models import Project, Question, Response, ProjectView, AnalyticsEvent

    create_resp = auth_client.post(
        "/api/projects/",
        json={
            "project_data": {"title": "Delete Cascade Test Project"},
            "question_data": {"text": "Will this be deleted?"},
        },
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["project"]["id"]
    question_id = create_resp.json()["question"]["id"]
    owner_id = create_resp.json()["project"]["owner_id"]

    db = SessionLocal()
    try:
        resp = Response(
            clarity="very_clear",
            would_use="yes",
            suggestion="Great!",
            question_id=question_id,
            user_id=owner_id,
            ip_hash="testiphash123",
        )
        db.add(resp)

        view = ProjectView(
            user_id=owner_id,
            project_id=project_id,
        )
        db.add(view)

        evt = AnalyticsEvent(
            event_name="feedback_view",
            visitor_id="testvisitor123",
            project_id=project_id,
        )
        db.add(evt)
        db.commit()

        assert db.query(Response).filter(Response.question_id == question_id).count() == 1
        assert db.query(Question).filter(Question.id == question_id).count() == 1
        assert db.query(ProjectView).filter(ProjectView.project_id == project_id).count() == 1
        assert db.query(AnalyticsEvent).filter(AnalyticsEvent.project_id == project_id).count() == 1
        assert db.query(Project).filter(Project.id == project_id).count() == 1

        del_resp = auth_client.delete(f"/api/projects/{project_id}")
        assert del_resp.status_code == 204

        assert db.query(Response).filter(Response.question_id == question_id).count() == 0
        assert db.query(Question).filter(Question.id == question_id).count() == 0
        assert db.query(ProjectView).filter(ProjectView.project_id == project_id).count() == 0
        assert db.query(AnalyticsEvent).filter(AnalyticsEvent.project_id == project_id).count() == 0
        assert db.query(Project).filter(Project.id == project_id).count() == 0

        second_del = auth_client.delete(f"/api/projects/{project_id}")
        assert second_del.status_code == 404
    finally:
        db.query(Response).filter(Response.question_id == question_id).delete()
        db.query(Question).filter(Question.project_id == project_id).delete()
        db.query(ProjectView).filter(ProjectView.project_id == project_id).delete()
        db.query(AnalyticsEvent).filter(AnalyticsEvent.project_id == project_id).delete()
        db.query(Project).filter(Project.id == project_id).delete()
        db.commit()
        db.close()

