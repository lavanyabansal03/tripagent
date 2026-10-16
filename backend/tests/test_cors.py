"""CORS behaviour for the deployed frontend.

The allowed origins come from CORS_ORIGINS so the same code serves local dev
(Vite on :5173) and production (the deployed frontend).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_local_dev_origin_is_allowed():
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_unknown_origin_is_not_echoed():
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
