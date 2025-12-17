from datetime import datetime

import src.utils.safe_network as safe_network
from src.core.ip_tracker import IPInfo, IPTracker


def test_get_public_ip_uses_safe_network_client(tmp_path, monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, method, url, **kwargs):
            return {"text": "203.0.113.10"}

    monkeypatch.setattr(safe_network, "HAS_REQUESTS", True)
    monkeypatch.setattr(safe_network, "SafeNetworkClient", FakeClient)

    tracker = IPTracker(storage_path=tmp_path)
    assert tracker._get_public_ip() == "203.0.113.10"


def test_get_public_ip_falls_back_on_invalid_response(tmp_path, monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, method, url, **kwargs):
            return {"text": "not-an-ip"}

    monkeypatch.setattr(safe_network, "HAS_REQUESTS", True)
    monkeypatch.setattr(safe_network, "SafeNetworkClient", FakeClient)

    tracker = IPTracker(storage_path=tmp_path)
    monkeypatch.setattr(tracker, "_get_local_ip", lambda: "127.0.0.1")
    assert tracker._get_public_ip() == "127.0.0.1"


def test_enrich_ip_info_parses_ipwho_response(tmp_path, monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, method, url, **kwargs):
            return {
                "success": True,
                "country": "Testland",
                "region": "Test Region",
                "city": "Test City",
                "connection": {"isp": "TestISP"},
                "security": {"proxy": True, "vpn": False},
            }

    monkeypatch.setattr(safe_network, "HAS_REQUESTS", True)
    monkeypatch.setattr(safe_network, "SafeNetworkClient", FakeClient)

    tracker = IPTracker(storage_path=tmp_path)
    ip_info = IPInfo(ip_address="203.0.113.10", timestamp=datetime.now())

    tracker._enrich_ip_info(ip_info)

    assert ip_info.country == "Testland"
    assert ip_info.region == "Test Region"
    assert ip_info.city == "Test City"
    assert ip_info.isp == "TestISP"
    assert ip_info.is_proxy is True
    assert ip_info.is_vpn is False
