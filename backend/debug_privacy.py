from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Project, Question, Response, User
from app.auth import get_current_user
from app.rate_limit import reset_rate_limits

reset_rate_limits()
db = SessionLocal()
db.query(Response).delete()
db.query(Question).delete()
db.query(Project).delete()
db.query(User).delete()
db.commit()

owner = User(github_id=111111, username='privacy_owner')
db.add(owner)
db.commit()
db.refresh(owner)
print(f'Owner ID: {owner.id}')

responder = User(github_id=222222, username='privacy_responder')
db.add(responder)
db.commit()
db.refresh(responder)
print(f'Responder ID: {responder.id}')
db.close()

app.dependency_overrides[get_current_user] = lambda: owner
owner_client = TestClient(app)
owner_client.cookies.set('critique_csrf', 'tok')
owner_client.headers['X-CSRF-Token'] = 'tok'
payload = {'project_data': {'title': 'Test', 'description': None, 'url': None, 'image_url': None}, 'question_data': {'text': 'Q?'}}
r = owner_client.post('/api/projects/', json=payload)
data = r.json()
pid = data['project']['id']
owner_id = data['project']['owner_id']
print(f'Project created: {pid}, owner_id={owner_id}')

app.dependency_overrides.clear()
app.dependency_overrides[get_current_user] = lambda: responder
responder_client = TestClient(app)
responder_client.cookies.set('critique_csrf', 'tok')
responder_client.headers['X-CSRF-Token'] = 'tok'
r_payload = {'clarity': 'very_clear', 'would_use': 'yes', 'suggestion': 'Private feedback'}
r = responder_client.post(f'/api/projects/{pid}/responses', json=r_payload)
print(f'Response submit: {r.status_code}')

r = responder_client.get(f'/api/projects/{pid}/responses')
print(f'Non-owner sees: {r.json()}')

app.dependency_overrides.clear()
app.dependency_overrides[get_current_user] = lambda: owner
r = owner_client.get(f'/api/projects/{pid}/responses')
print(f'Owner sees: {r.json()}')

app.dependency_overrides.clear()
