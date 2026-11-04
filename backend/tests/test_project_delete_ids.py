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
