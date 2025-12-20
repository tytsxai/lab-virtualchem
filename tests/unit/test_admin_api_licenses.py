from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("flask")
pytest.importorskip("flask_cors")

from src.api.admin_api import AdminAPI
from src.core.device_fingerprint import DeviceAuthManager
from src.core.license_manager import CryptoPayment, LicenseManager, LicenseType


def _build_license(manager: LicenseManager) -> str:
    payment = CryptoPayment(
        currency="ETH",
        tx_hash="0xabc",
        amount=1.5,
        recipient_address="0xdef",
        timestamp=datetime.now(),
    )
    license_obj = manager.generate_license(
        user_id="user-1",
        email="user@example.com",
        machine_id="machine-1",
        license_type=LicenseType.PERSONAL,
        payment=payment,
        validity_days=30,
    )
    license_obj.is_activated = True
    manager.save_license(license_obj)
    return license_obj.license_key


def _make_admin_api(tmp_path: Path, license_file: Path) -> AdminAPI:
    manager = LicenseManager(
        secret_key="signing-secret-key-32-chars-000000",
        license_file=license_file,
    )
    device_manager = DeviceAuthManager(storage_path=tmp_path / "device_auth")
    admin_secret = "admin-secret-key-32-chars-0000000"
    return AdminAPI(
        license_manager=manager,
        device_auth_manager=device_manager,
        admin_secret=admin_secret,
        host="127.0.0.1",
        port=5000,
    )


def test_list_licenses_returns_license(tmp_path):
    license_file = tmp_path / "license.json"
    api = _make_admin_api(tmp_path, license_file)
    license_key = _build_license(api.license_manager)

    client = api.app.test_client()
    response = client.get("/api/licenses", headers={"X-Admin-Secret": api._admin_secret})

    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 1
    assert data["licenses"][0]["license_key"] == license_key
    assert data["licenses"][0]["status"] in {"active", "inactive", "expired"}


def test_list_licenses_empty(tmp_path):
    license_file = tmp_path / "missing.json"
    api = _make_admin_api(tmp_path, license_file)

    client = api.app.test_client()
    response = client.get("/api/licenses", headers={"X-Admin-Secret": api._admin_secret})

    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 0
