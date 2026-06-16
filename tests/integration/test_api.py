from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_no_file():
    resp = client.post("/api/v1/upload")
    assert resp.status_code == 422


def test_analyze_invalid_id():
    resp = client.post("/api/v1/analyze", json={"contract_id": "nonexistent"})
    assert resp.status_code == 404


def test_chat_missing_fields():
    resp = client.post("/api/v1/chat", json={})
    assert resp.status_code == 422
