from fastapi.testclient import TestClient
from app import app
with TestClient(app) as client:
    print(client.get('/api/debug').json())
