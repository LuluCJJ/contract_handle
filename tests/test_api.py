from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_demo_cases_are_listed():
    response = client.get("/api/demo-cases")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 10
    assert any(item["package_id"] == "PKG-DEMO-001" for item in data)


def test_legacy_case_uses_real_document_assets():
    response = client.get("/api/packages/PKG-CASE-001-PASS")
    assert response.status_code == 200
    data = response.json()
    document = data["submitted_documents"][0]
    assert document["file_name"] == "bank_app.docx"
    assert document["file_type"] == "docx"
    assert document["preview_url"].endswith("/case_001_pass/bank_app.docx")
    assert document["preview_text"]
    assert data["identity_documents"][0]["file_type"] == "jpg"


def test_pdf_case_is_in_demo_matrix():
    response = client.get("/api/packages/PKG-CASE-014-PDF-PASS")
    assert response.status_code == 200
    document = response.json()["submitted_documents"][0]
    assert document["file_name"] == "bank_app.pdf"
    assert document["file_type"] == "pdf"
    assert document["preview_url"].endswith("/case_014_boc_domestic_pass/bank_app.pdf")


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


def test_create_upload_package_and_run_comparison():
    upload_response = client.post(
        "/api/upload-package",
        json={
            "company": "Demo Upload Company Limited",
            "bank": "Demo Bank",
            "platform": "Corporate Online Banking",
            "activity": "open",
            "account_number": "9988776655",
            "user_name": "Upload Tester",
            "identity_doc_type": "Passport",
            "identity_doc_no": "P-UPLOAD-001",
            "permissions": ["query", "payment"],
            "media": ["Token"],
            "single_limit": 500000,
            "submitted_files": [
                {
                    "file_name": "uploaded-application.txt",
                    "file_type": "txt",
                    "text": "\n".join(
                        [
                            "Activity: open",
                            "User Count: 1",
                            "Company Name: Demo Upload Company Limited",
                            "Account Number: 9988776655",
                            "Operator Name: Upload Tester",
                            "Identity Doc Type: Passport",
                            "Identity Doc No: P-UPLOAD-001",
                            "Permissions: query, payment, admin approval",
                            "Media: Token",
                            "Single Limit: 500000",
                            "Declaration: Standard corporate online banking application terms remain unchanged.",
                        ]
                    ),
                }
            ],
            "template_file": {
                "file_name": "uploaded-template.txt",
                "file_type": "txt",
                "text": "\n".join(
                    [
                        "Activity: open",
                        "User Count: 1",
                        "Company Name: Demo Upload Company Limited",
                        "Account Number: 9988776655",
                        "Operator Name: Upload Tester",
                        "Identity Doc Type: Passport",
                        "Identity Doc No: P-UPLOAD-001",
                        "Permissions: query, payment",
                        "Media: Token",
                        "Single Limit: 500000",
                        "Declaration: Standard corporate online banking application terms remain unchanged.",
                    ]
                ),
            },
        },
    )
    assert upload_response.status_code == 200
    created = upload_response.json()
    assert created["package_id"].startswith("PKG-UPLOAD-")
    assert created["template_version_id"].startswith("TPLV-UPLOAD-")

    comparison_response = client.post(
        f"/api/packages/{created['package_id']}/run-comparison",
        json={
            "strategies": ["block_rule_check", "template_plus_diff", "full_agent_review"],
            "options": {"use_mock_llm": True},
        },
    )
    assert comparison_response.status_code == 200
    data = comparison_response.json()
    assert len(data["reports"]) == 3
    assert sum(report["metrics"]["detected_issues_count"] for report in data["reports"]) >= 1
