from app.database import init_db, SessionLocal
from app.models import User, Project, Question, Response


def test_database_tables_exist():
    """Test that all expected tables are created."""
    init_db()
    db = SessionLocal()
    try:
        # Query each table to verify it exists
        users = db.query(User).all()
        projects = db.query(Project).all()
        questions = db.query(Question).all()
        responses = db.query(Response).all()

        # All queries should return empty lists (no data yet)
        assert users == []
        assert projects == []
        assert questions == []
        assert responses == []
    finally:
        db.close()


def test_create_full_chain():
    """Test creating a full chain: User -> Project -> Question -> Response."""
    init_db()
    db = SessionLocal()
    try:
        # Create user
        user = User(github_id=12345, username="testuser")
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create project
        project = Project(title="Test Project", description="A test", owner_id=user.id)
        db.add(project)
        db.commit()
        db.refresh(project)

        # Create question
        question = Question(text="What do you think?", project_id=project.id)
        db.add(question)
        db.commit()
        db.refresh(question)

        # Create response with new structured fields
        response = Response(
            clarity="very_clear",
            would_use="yes",
            suggestion="Looks great!",
            question_id=question.id,
            user_id=user.id,
            ip_hash="test_hash_123",
        )
        db.add(response)
        db.commit()
        db.refresh(response)

        # Verify relationships
        assert user.projects[0].id == project.id
        assert project.questions[0].id == question.id
        assert question.responses[0].id == response.id
        assert response.user_id == user.id
        assert response.clarity == "very_clear"
        assert response.would_use == "yes"

        # Clean up (delete in reverse order)
        db.delete(response)
        db.delete(question)
        db.delete(project)
        db.delete(user)
        db.commit()
    finally:
        db.close()
