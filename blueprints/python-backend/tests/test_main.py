from app.main import app
from fastapi.testclient import TestClient


def test_hello() -> None:
    assert TestClient(app).get("/api/hello").json() == {"message": "hello"}

