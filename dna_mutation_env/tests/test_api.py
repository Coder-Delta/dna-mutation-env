from fastapi.testclient import TestClient

from dna_mutation_env.server.app import app


def test_root_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "DNA Mutation OpenEnv" in response.text
    assert "Compact Dark UI" in response.text
    assert 'id="reset-btn"' in response.text


def test_app_info_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/app-info")
    assert response.status_code == 200
    assert response.json()["name"] == "DNA Mutation OpenEnv"
    assert response.json()["docs_url"] == "/docs"


def test_ready_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
