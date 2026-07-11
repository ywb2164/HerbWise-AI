from fastapi.testclient import TestClient

from app.main import create_app


def test_health_is_alive() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert "x-request-id" in response.headers
