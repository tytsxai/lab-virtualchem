import asyncio
import json


def _write_license_config(tmp_path, *, secret_key=None, strict_mode=False, trial_days=7):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "crypto_payment_config.json"
    payload = {"license": {"strict_mode": strict_mode, "trial_days": trial_days}}
    if secret_key is not None:
        payload["license"]["secret_key"] = secret_key
    config_file.write_text(json.dumps(payload), encoding="utf-8")


class _DummyLicenseManager:
    def __init__(self, secret_key, license_file):
        self.secret_key = secret_key
        self.license_file = license_file

    def get_license_info(self, _license_obj):
        return {
            "license_type": "trial",
            "email": "test@example.com",
            "days_remaining": 999,
        }


class _DummyMiddlewareBase:
    def __init__(self, license_manager, strict_mode=False, trial_days=7):
        self.license_manager = license_manager
        self.strict_mode = strict_mode
        self.trial_days = trial_days

    async def process(self, _context, next_middleware):
        return await next_middleware()

    def get_current_license(self):
        return None


def test_check_license_missing_secret_key_fail_closed(monkeypatch, tmp_path):
    import src.main_with_license as mwl

    monkeypatch.setattr(mwl, "PROJECT_ROOT", tmp_path)
    _write_license_config(tmp_path, secret_key=None)

    assert mwl.check_license() is False


def test_check_license_generic_exception_fail_closed(monkeypatch, tmp_path):
    import src.main_with_license as mwl

    class ExplodingMiddleware(_DummyMiddlewareBase):
        async def process(self, _context, _next_middleware):
            raise RuntimeError("boom")

    monkeypatch.setattr(mwl, "PROJECT_ROOT", tmp_path)
    _write_license_config(tmp_path, secret_key="unit-test-secret")

    monkeypatch.setattr(mwl, "LicenseManager", _DummyLicenseManager)
    monkeypatch.setattr(mwl, "LicenseMiddleware", ExplodingMiddleware)

    assert mwl.check_license() is False


def test_check_license_timeout_exception_allows_degraded_start(monkeypatch, tmp_path):
    import src.main_with_license as mwl

    class TimeoutMiddleware(_DummyMiddlewareBase):
        async def process(self, _context, _next_middleware):
            raise asyncio.TimeoutError()

    monkeypatch.setattr(mwl, "PROJECT_ROOT", tmp_path)
    _write_license_config(tmp_path, secret_key="unit-test-secret")

    monkeypatch.setattr(mwl, "LicenseManager", _DummyLicenseManager)
    monkeypatch.setattr(mwl, "LicenseMiddleware", TimeoutMiddleware)

    assert mwl.check_license() is True


def test_check_license_uses_run_until_complete_when_loop_exists(monkeypatch, tmp_path):
    import src.main_with_license as mwl

    monkeypatch.setattr(mwl, "PROJECT_ROOT", tmp_path)
    _write_license_config(tmp_path, secret_key="unit-test-secret", strict_mode=False)

    monkeypatch.setattr(mwl, "LicenseManager", _DummyLicenseManager)
    monkeypatch.setattr(mwl, "LicenseMiddleware", _DummyMiddlewareBase)

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)

        def _should_not_be_called(*_args, **_kwargs):
            raise AssertionError("asyncio.run() should not be used when a loop exists")

        monkeypatch.setattr(mwl.asyncio, "run", _should_not_be_called)

        assert mwl.check_license() is True
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_check_license_running_loop_fail_closed(monkeypatch, tmp_path):
    import src.main_with_license as mwl

    monkeypatch.setattr(mwl, "PROJECT_ROOT", tmp_path)
    _write_license_config(tmp_path, secret_key="unit-test-secret", strict_mode=False)
    monkeypatch.setattr(mwl, "LicenseManager", _DummyLicenseManager)
    monkeypatch.setattr(mwl, "LicenseMiddleware", _DummyMiddlewareBase)

    async def _run_inside_loop():
        return mwl.check_license()

    assert asyncio.run(_run_inside_loop()) is False

