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


def test_mcp_lists_tools() -> None:
    client = TestClient(app)
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jsonrpc"] == "2.0"
    tool_names = {tool["name"] for tool in payload["result"]["tools"]}
    assert {"reset_episode", "get_observation", "get_state", "take_action"} <= tool_names


def test_mcp_can_call_reset_and_action_tools() -> None:
    client = TestClient(app)

    reset_response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "reset_episode",
                "arguments": {"task_id": "medium_indel_low_coverage", "seed": 9},
            },
        },
    )
    assert reset_response.status_code == 200
    reset_payload = reset_response.json()
    assert (
        reset_payload["result"]["observation"]["task_id"]
        == "medium_indel_low_coverage"
    )
    assert reset_payload["result"]["observation"]["done"] is False

    action_response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "take_action",
                "arguments": {
                    "action_type": "submit_answer",
                    "locus": 5,
                    "end": 5,
                    "variant_type": "snv",
                    "ref_allele": "A",
                    "alt_allele": "G",
                    "confidence": 0.99,
                    "reasoning": "Submit the exact SNV call.",
                },
            },
        },
    )

    assert action_response.status_code == 200
    action_payload = action_response.json()
    assert action_payload["result"]["done"] is True
    assert action_payload["result"]["reward"] >= 0.9
