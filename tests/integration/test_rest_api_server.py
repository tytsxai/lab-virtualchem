"""Integration tests for the REST API server (HTTPServer based)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
import requests
import yaml

from src import __version__ as APP_VERSION
from src.api.server import APIServer


@pytest.fixture
def running_api_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Start APIServer on an ephemeral port with isolated home/config + templates."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("VCL_API_KEYS", "test_api_key,test_admin_key")
    monkeypatch.setenv("VCL_API_ADMIN_KEYS", "test_admin_key")
    # Probes expect these secrets to exist and be strong enough.
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("SESSION_SECRET_KEY", "y" * 32)
    monkeypatch.setenv("VCL_ADMIN_SECRET_KEY", "z" * 32)
    monkeypatch.setenv("VCL_HEALTH_DIR", str(tmp_path / "health"))

    config_dir = tmp_path / ".virtualchemlab"
    config_dir.mkdir(parents=True, exist_ok=True)

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    template_data = {
        "experiment": {
            "id": "test_exp_001",
            "title": "测试滴定实验",
            "level": "basic",
            "category": "酸碱滴定",
            "description": "用于 REST API 集成测试的滴定实验",
            "steps": [
                {
                    "id": "step1",
                    "title": "准备溶液",
                    "text": "准备标准溶液和待测溶液",
                    "inputs": [
                        {
                            "id": "volume_naoh",
                            "label": "NaOH体积",
                            "type": "number",
                            "unit": "mL",
                            "min_value": 0,
                            "max_value": 50,
                        }
                    ],
                    "validation_rules": [
                        {
                            "type": "range",
                            "field": "volume_naoh",
                            "min": 10,
                            "max": 30,
                            "error_message": "体积应在10-30mL之间",
                        }
                    ],
                    "correct_value": 25.0,
                },
                {
                    "id": "step2",
                    "title": "进行滴定",
                    "text": "使用标准溶液滴定待测溶液",
                    "inputs": [
                        {
                            "id": "volume_used",
                            "label": "消耗体积",
                            "type": "number",
                            "unit": "mL",
                            "min_value": 0,
                            "max_value": 50,
                        }
                    ],
                    "validation_rules": [
                        {
                            "type": "range",
                            "field": "volume_used",
                            "min": 20,
                            "max": 30,
                            "error_message": "消耗体积异常",
                        }
                    ],
                    "correct_value": 24.5,
                },
            ],
        }
    }

    (templates_dir / "test_exp_001.yaml").write_text(
        yaml.dump(template_data, allow_unicode=True),
        encoding="utf-8",
    )

    data_dir = tmp_path / "records"
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "paths": {
                    "templates_dir": str(templates_dir),
                    "data_dir": str(data_dir),
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    server = APIServer(
        host="127.0.0.1",
        port=0,
        enable_auth=True,
        enable_rate_limit=False,
    )
    try:
        server.start()
    except PermissionError as exc:
        pytest.skip(f"Sandbox forbids binding local HTTP server: {exc}")
    except OSError as exc:
        pytest.skip(f"Cannot start local HTTP server in this environment: {exc}")
    assert server.server is not None
    port = int(server.server.server_address[1])
    base_url = f"http://127.0.0.1:{port}"

    try:
        for _ in range(50):
            try:
                resp = requests.get(f"{base_url}/api/health", timeout=1)
                if resp.status_code == 200:
                    break
            except requests.RequestException:
                time.sleep(0.05)
        else:
            pytest.fail("APIServer did not become ready in time")

        yield base_url
    finally:
        server.stop()
        if server.thread:
            server.thread.join(timeout=2)


def test_rest_api_flow_creates_record_and_report(running_api_server: str) -> None:
    base_url = running_api_server

    unauthorized = requests.get(f"{base_url}/api/experiments", timeout=5)
    assert unauthorized.status_code == 401

    headers = {"X-API-Key": "test_api_key"}

    experiments_resp = requests.get(
        f"{base_url}/api/experiments", headers=headers, timeout=5
    )
    assert experiments_resp.status_code == 200
    experiments_payload = experiments_resp.json()
    assert experiments_payload["success"] is True
    experiments = experiments_payload["data"]["experiments"]
    assert any(exp.get("id") == "test_exp_001" for exp in experiments)

    start_resp = requests.post(
        f"{base_url}/api/experiments/start",
        headers=headers,
        json={"experiment_id": "test_exp_001", "user_id": "test_user"},
        timeout=5,
    )
    assert start_resp.status_code == 201
    session_id = start_resp.json()["session_id"]

    step1_resp = requests.post(
        f"{base_url}/api/experiments/submit",
        headers=headers,
        json={"session_id": session_id, "data": {"volume_naoh": 25.0}},
        timeout=5,
    )
    assert step1_resp.status_code == 200
    assert step1_resp.json()["passed"] is True
    assert step1_resp.json()["has_next_step"] is True

    step2_resp = requests.post(
        f"{base_url}/api/experiments/submit",
        headers=headers,
        json={"session_id": session_id, "data": {"volume_used": 24.5}},
        timeout=5,
    )
    assert step2_resp.status_code == 200
    assert step2_resp.json()["passed"] is True
    assert step2_resp.json()["has_next_step"] is False
    assert step2_resp.json()["current_step"] is None

    finish_resp = requests.post(
        f"{base_url}/api/experiments/finish",
        headers=headers,
        json={"session_id": session_id},
        timeout=10,
    )
    assert finish_resp.status_code == 200
    record_id = finish_resp.json()["record_id"]
    assert record_id

    records_resp = requests.get(
        f"{base_url}/api/records",
        headers=headers,
        params={"user_id": "test_user"},
        timeout=5,
    )
    assert records_resp.status_code == 200
    records = records_resp.json()["records"]
    assert any(rec.get("id") == record_id for rec in records)

    record_resp = requests.get(
        f"{base_url}/api/records/{record_id}",
        headers=headers,
        params={"user_id": "test_user"},
        timeout=5,
    )
    assert record_resp.status_code == 200
    record = record_resp.json()["record"]
    assert record["record_id"] == record_id
    assert record["user_id"] == "test_user"

    report_resp = requests.post(
        f"{base_url}/api/reports/generate",
        headers=headers,
        json={"record_id": record_id, "format": "html"},
        timeout=10,
    )
    assert report_resp.status_code == 200
    report = report_resp.json()

    assert report["record_id"] == record_id
    assert report["format"] == "html"
    assert report["path"] == str(Path("reports") / f"{record_id}.html")
    assert Path(report["path"]).exists()


def test_rest_api_does_not_allow_query_param_auth_bypass(running_api_server: str) -> None:
    base_url = running_api_server
    resp = requests.get(
        f"{base_url}/api/experiments",
        params={"api_key": "test_api_key"},
        timeout=5,
    )
    assert resp.status_code == 401


def test_rest_api_rejects_unknown_fields_in_post_body(running_api_server: str) -> None:
    base_url = running_api_server
    headers = {"X-API-Key": "test_api_key"}
    resp = requests.post(
        f"{base_url}/api/experiments/start",
        headers=headers,
        json={
            "experiment_id": "test_exp_001",
            "user_id": "test_user",
            "unexpected": "nope",
        },
        timeout=5,
    )
    assert resp.status_code in (400, 422)  # 422 is standard for Pydantic validation errors
    payload = resp.json()
    assert payload["success"] is False
    assert payload["error"]["type"] == "DATA_VALIDATION_FAILED"


def test_rest_api_rejects_unknown_fields_in_query(running_api_server: str) -> None:
    base_url = running_api_server
    headers = {"X-API-Key": "test_api_key"}
    resp = requests.get(
        f"{base_url}/api/records",
        headers=headers,
        params={"user_id": "test_user", "unexpected": "nope"},
        timeout=5,
    )
    assert resp.status_code in (400, 422)  # 422 is standard for Pydantic validation errors
    payload = resp.json()
    assert payload["success"] is False
    assert payload["error"]["type"] == "DATA_VALIDATION_FAILED"


def test_probes_and_metrics(running_api_server: str) -> None:
    base_url = running_api_server
    headers = {"X-API-Key": "test_api_key"}
    admin_headers = {"X-API-Key": "test_admin_key"}

    healthz = requests.get(f"{base_url}/healthz", timeout=5)
    assert healthz.status_code == 200
    payload = healthz.json()
    assert payload["version"] == APP_VERSION
    assert payload["build"]["version"] == APP_VERSION

    readyz = requests.get(f"{base_url}/readyz", timeout=5)
    assert readyz.status_code == 200
    assert readyz.json()["status"] == "ready"

    metrics_unauth = requests.get(f"{base_url}/metrics", timeout=5)
    assert metrics_unauth.status_code == 401

    metrics = requests.get(
        f"{base_url}/metrics", headers=headers, timeout=5
    )
    assert metrics.status_code == 403

    metrics_admin = requests.get(
        f"{base_url}/metrics", headers=admin_headers, timeout=5
    )
    assert metrics_admin.status_code == 200
    assert "vcl_api_requests_total" in metrics_admin.text
