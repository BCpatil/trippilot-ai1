from fastapi.testclient import TestClient

from trippilot.main import app

client = TestClient(app)


def test_liveness_endpoint_reports_alive() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
