from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User
from app.auth import get_current_user

db = SessionLocal()
user = db.query(User).first()
if user:
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    client.cookies.set('critique_csrf', 'test')
    client.headers['X-CSRF-Token'] = 'test'
    
    payload = {'clarity': 'very_clear', 'would_use': 'yes', 'suggestion': 'test'}
    resp = client.post('/api/projects/1/responses', json=payload)
    print('Status:', resp.status_code)
    print('Body:', resp.text[:200])
    print('Content-Type:', resp.headers.get('content-type'))
    app.dependency_overrides.clear()
db.close()
