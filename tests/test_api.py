from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_demo_cases_are_listed():
    response = client.get("/api/demo-cases")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 8
    assert any(item["package_id"] == "PKG-DEMO-001" for item in data)


def test_run_preaudit_with_mock_llm():
    response = client.post(
        "/api/packages/PKG-DEMO-001/run-preaudit",
        json={"strategy": "template_plus_diff", "options": {"use_mock_llm": True}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "template_plus_diff"
    assert data["metrics"]["llm_calls"] >= 1
    assert data["results"]


def test_demo_suite_with_mock_llm():
    response = client.post(
        "/api/demo-suite/run",
        json={
            "strategies": ["block_rule_check", "template_plus_diff"],
            "options": {"use_mock_llm": True},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["case_count"] >= 8
    assert all(row["reports"] for row in data["rows"])
