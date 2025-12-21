import os
import sys
import importlib
import threading
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def _restore_global_exception_hooks():
    old_sys_hook = sys.excepthook
    old_thread_hook = getattr(threading, "excepthook", None)
    yield
    sys.excepthook = old_sys_hook
    if old_thread_hook is not None and hasattr(threading, "excepthook"):
        threading.excepthook = old_thread_hook  # type: ignore[assignment]


class _DummySignal:
    def __init__(self) -> None:
        self._connected = []

    def connect(self, fn):  # noqa: ANN001
        self._connected.append(fn)


class _DummyApp:
    last_instance = None

    def __init__(self, argv):  # noqa: ANN001
        self.argv = list(argv)
        self.aboutToQuit = _DummySignal()
        self._exec_result = 42
        _DummyApp.last_instance = self

    def setApplicationName(self, _):  # noqa: ANN001
        return None

    def setApplicationDisplayName(self, _):  # noqa: ANN001
        return None

    def setApplicationVersion(self, _):  # noqa: ANN001
        return None

    def setOrganizationName(self, _):  # noqa: ANN001
        return None

    def exec(self) -> int:
        return self._exec_result


class _DummyQt:
    AA_EnableHighDpiScaling = object()
    AA_UseHighDpiPixmaps = object()


class _DummyContainer:
    def __init__(self) -> None:
        self._services = [object(), object(), object()]

    def get_all_services(self):  # noqa: ANN001
        return self._services


def _install_fake_qt_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    pyside6 = ModuleType("PySide6")
    qtcore = ModuleType("PySide6.QtCore")
    qtwidgets = ModuleType("PySide6.QtWidgets")
    qtcore.Qt = _DummyQt
    qtwidgets.QApplication = _DummyApp
    monkeypatch.setitem(sys.modules, "PySide6", pyside6)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", qtcore)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qtwidgets)


def _install_fake_ui_modules(monkeypatch: pytest.MonkeyPatch) -> dict:
    qt_sanity = ModuleType("src.ui.qt_sanity")
    calls: dict[str, object] = {"abort": None, "window_shown": False}

    def ensure_single_qt_binding(*, abort: bool) -> None:
        calls["abort"] = abort

    qt_sanity.ensure_single_qt_binding = ensure_single_qt_binding  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.ui.qt_sanity", qt_sanity)

    main_window = ModuleType("src.ui.main_window")

    class MainWindow:  # noqa: D401
        def __init__(self, *, container):  # noqa: ANN001
            self.container = container

        def show(self) -> None:
            calls["window_shown"] = True

    main_window.MainWindow = MainWindow  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.ui.main_window", main_window)

    responsive = ModuleType("src.ui.responsive")

    class DPIHelper:
        @staticmethod
        def enable_high_dpi_scaling() -> None:
            return None

    responsive.DPIHelper = DPIHelper  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.ui.responsive", responsive)

    return calls


def _import_main_with_core_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    get_config_impl,
    configure_container_impl,
    ensure_secure_startup_impl,
    setup_logger_impl,
) -> ModuleType:
    """
    Import `src.main` while stubbing heavy core modules at import time.

    `src.main` imports `src.core.service_registration` at module import time; in this
    repo that can transitively import many heavy modules. For unit tests we keep the
    dependency surface tiny by stubbing those modules before importing `src.main`.
    """

    config_loader = ModuleType("src.core.config_loader")
    config_loader.get_config = get_config_impl  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.core.config_loader", config_loader)

    service_registration = ModuleType("src.core.service_registration")
    service_registration.configure_container = configure_container_impl  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.core.service_registration", service_registration)

    startup_preflight = ModuleType("src.core.startup_preflight")
    startup_preflight.ensure_secure_startup = ensure_secure_startup_impl  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.core.startup_preflight", startup_preflight)

    logger_mod = ModuleType("src.utils.logger")

    def _get_logger(_name: str):  # noqa: ANN001
        import logging

        return logging.getLogger(_name)

    logger_mod.get_logger = _get_logger  # type: ignore[attr-defined]
    logger_mod.setup_logger = setup_logger_impl  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.utils.logger", logger_mod)

    sys.modules.pop("src.main", None)
    return importlib.import_module("src.main")


def test_main_happy_path_installs_cleanup_and_runs_event_loop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake_qt_modules(monkeypatch)
    ui_calls = _install_fake_ui_modules(monkeypatch)

    call_order: list[str] = []

    config = SimpleNamespace(
        app=SimpleNamespace(environment="test", debug=False),
        paths=SimpleNamespace(logs="logs"),
        log=SimpleNamespace(
            file="app.log",
            level="INFO",
            max_size=1024,
            backup_count=1,
        ),
    )

    def fake_get_config():  # noqa: ANN001
        call_order.append("get_config")
        return config

    def fake_setup_logger(*args, **kwargs):  # noqa: ANN001
        call_order.append("setup_logger")
        return None

    def fake_ensure_secure_startup(*, config):  # noqa: ANN001
        assert config is not None
        call_order.append("ensure_secure_startup")

    def fake_configure_container(*, config):  # noqa: ANN001
        assert config is not None
        call_order.append("configure_container")
        return _DummyContainer()

    registered: list[object] = []

    def fake_atexit_register(fn):  # noqa: ANN001
        registered.append(fn)

    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=fake_get_config,
        configure_container_impl=fake_configure_container,
        ensure_secure_startup_impl=fake_ensure_secure_startup,
        setup_logger_impl=fake_setup_logger,
    )
    monkeypatch.setattr(main_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(main_mod.atexit, "register", fake_atexit_register)
    monkeypatch.setattr(sys, "argv", ["prog", "--env", "development", "--other"])

    result = main_mod.main()

    assert result == 42
    assert _DummyApp.last_instance is not None
    assert _DummyApp.last_instance.aboutToQuit._connected, "aboutToQuit should connect cleanup"
    assert ui_calls["abort"] is True
    assert ui_calls["window_shown"] is True
    assert os.environ.get("ENVIRONMENT") == "development"
    assert sys.argv == ["prog", "--other"]
    assert call_order[0] == "setup_logger"  # import-time default logger setup
    assert "get_config" in call_order
    assert call_order.count("setup_logger") >= 2  # import-time + file logger init
    assert "ensure_secure_startup" in call_order
    assert "configure_container" in call_order
    assert registered, "atexit.register should be called to install cleanup hook"

    shutdown_calls: list[str] = []
    monkeypatch.setattr(main_mod.logging, "shutdown", lambda: shutdown_calls.append("shutdown"))
    registered[0]()
    assert shutdown_calls == ["shutdown"]


def test_main_returns_1_when_pyside6_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    sys.modules.pop("PySide6.QtCore", None)
    sys.modules.pop("PySide6.QtWidgets", None)
    sys.modules.pop("PySide6", None)
    # tests/conftest.py prepends a PySide6 stub to sys.path; remove it here to
    # ensure the import truly fails and we hit the ImportError branch.
    monkeypatch.setattr(
        sys,
        "path",
        [p for p in sys.path if "tests/fixtures/pyside6_stub" not in p],
        raising=False,
    )

    qt_sanity = ModuleType("src.ui.qt_sanity")
    qt_sanity.ensure_single_qt_binding = lambda *, abort: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.ui.qt_sanity", qt_sanity)

    config = SimpleNamespace(
        app=SimpleNamespace(environment="test", debug=False),
        paths=SimpleNamespace(logs="logs"),
        log=SimpleNamespace(file="app.log", level="INFO", max_size=1, backup_count=1),
    )

    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: config,
        configure_container_impl=lambda *, config: _DummyContainer(),
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )
    monkeypatch.setattr(
        main_mod, "_resolve_log_file_path", lambda *_args, **_kw: Path("logs/app.log")
    )

    assert main_mod.main() == 1


def test_helpers_cover_log_path_and_cli_and_redaction(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: SimpleNamespace(),
        configure_container_impl=lambda *, config: _DummyContainer(),
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )

    cfg = SimpleNamespace(paths=SimpleNamespace(logs="logs"), log=SimpleNamespace(file="/abs/pwn.log"))
    resolved = main_mod._resolve_log_file_path(cfg, project_root=tmp_path)
    assert resolved.name == "pwn.log"

    cfg2 = SimpleNamespace(paths=SimpleNamespace(logs="logs"), log=SimpleNamespace(file="logs/app.log"))
    resolved2 = main_mod._resolve_log_file_path(cfg2, project_root=tmp_path)
    assert resolved2.as_posix().endswith("/logs/app.log")

    cfg3 = SimpleNamespace(paths=SimpleNamespace(logs="logs"), log=SimpleNamespace(file="../escape.log"))
    resolved3 = main_mod._resolve_log_file_path(cfg3, project_root=tmp_path)
    assert resolved3.name == "app.log"

    assert main_mod._apply_cli_environment_overrides(["prog"]) == ["prog"]
    os.environ.pop("ENVIRONMENT", None)
    assert main_mod._apply_cli_environment_overrides(["prog", "--env=dev", "--x"]) == ["prog", "--x"]
    assert os.environ.get("ENVIRONMENT") == "dev"

    assert main_mod._redact_startup_error(RuntimeError("secret")) == "RuntimeError"


def test_exception_hooks_emit_critical(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: SimpleNamespace(),
        configure_container_impl=lambda *, config: _DummyContainer(),
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )

    caplog.set_level(main_mod.logging.CRITICAL, logger="virtualchemlab")
    main_mod._install_global_exception_hooks()
    sys.excepthook(RuntimeError, RuntimeError("x"), None)  # type: ignore[arg-type]
    if hasattr(threading, "excepthook"):
        args = SimpleNamespace(exc_type=RuntimeError, exc_value=RuntimeError("x"), exc_traceback=None)
        threading.excepthook(args)  # type: ignore[arg-type]
    critical_records = [r for r in caplog.records if r.levelno >= main_mod.logging.CRITICAL]
    assert len(critical_records) >= 2


def test_main_get_config_oserror_is_redacted_and_returns_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class SecretOSError(OSError):
        pass

    exc = SecretOSError("secret: /private/path/config.json")
    exc.errno = 13

    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: (_ for _ in ()).throw(exc),
        configure_container_impl=lambda *, config: _DummyContainer(),
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )

    result = main_mod.main()
    captured = capsys.readouterr()

    assert result == 1
    assert "secret" not in captured.err
    assert "private" not in captured.err
    assert "SecretOSError" in captured.err
    assert "errno=13" in captured.err


def test_main_dpihelper_failure_falls_back_to_qt_attributes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake_qt_modules(monkeypatch)
    _install_fake_ui_modules(monkeypatch)

    responsive = ModuleType("src.ui.responsive")

    class DPIHelper:
        @staticmethod
        def enable_high_dpi_scaling() -> None:
            raise RuntimeError("boom")

    responsive.DPIHelper = DPIHelper  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.ui.responsive", responsive)

    set_attrs: list[object] = []

    def set_attribute(attr, value):  # noqa: ANN001
        set_attrs.append((attr, value))

    from PySide6 import QtWidgets as qtwidgets  # type: ignore

    qtwidgets.QApplication.setAttribute = staticmethod(set_attribute)  # type: ignore[attr-defined]

    config = SimpleNamespace(
        app=SimpleNamespace(environment="test", debug=False),
        paths=SimpleNamespace(logs="logs"),
        log=SimpleNamespace(file="app.log", level="INFO", max_size=1, backup_count=1),
    )

    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: config,
        configure_container_impl=lambda *, config: _DummyContainer(),
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )
    monkeypatch.setattr(main_mod, "PROJECT_ROOT", tmp_path)

    assert main_mod.main() == 42
    assert set_attrs, "Should set Qt high-DPI attributes on DPIHelper failure"


def test_main_returns_0_on_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_qt_modules(monkeypatch)
    _install_fake_ui_modules(monkeypatch)

    config = SimpleNamespace(
        app=SimpleNamespace(environment="test", debug=False),
        paths=SimpleNamespace(logs="logs"),
        log=SimpleNamespace(file="app.log", level="INFO", max_size=1, backup_count=1),
    )

    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: config,
        configure_container_impl=lambda *, config: _DummyContainer(),
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )

    def _exec_raises(self):  # noqa: ANN001
        raise KeyboardInterrupt

    from PySide6 import QtWidgets as qtwidgets  # type: ignore

    monkeypatch.setattr(qtwidgets.QApplication, "exec", _exec_raises, raising=False)
    assert main_mod.main() == 0


def test_main_returns_1_on_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_qt_modules(monkeypatch)
    _install_fake_ui_modules(monkeypatch)

    config = SimpleNamespace(
        app=SimpleNamespace(environment="test", debug=False),
        paths=SimpleNamespace(logs="logs"),
        log=SimpleNamespace(file="app.log", level="INFO", max_size=1, backup_count=1),
    )

    def boom(*, config):  # noqa: ANN001
        raise RuntimeError("crash")

    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: config,
        configure_container_impl=boom,
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )

    assert main_mod.main() == 1


def test_test_core_only_exercises_template_and_curve_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = SimpleNamespace(app=SimpleNamespace(name="X", version="1.0"))

    class _CoreContainer(_DummyContainer):
        def resolve(self, cls):  # noqa: ANN001
            if cls.__name__ == "TemplateEngine":
                return SimpleNamespace(list_available_experiments=lambda: [])
            if cls.__name__ == "CurveGenerator":
                return SimpleNamespace(generate_titration_curve=lambda **_: ([1, 2, 3],))
            raise KeyError(cls)

    def fake_configure_container(*, config):  # noqa: ANN001
        return _CoreContainer()

    template_engine_mod = ModuleType("src.core.template_engine")

    class TemplateEngine:  # noqa: D401
        pass

    template_engine_mod.TemplateEngine = TemplateEngine  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.core.template_engine", template_engine_mod)

    curve_generator_mod = ModuleType("src.core.curve_generator")

    class CurveGenerator:  # noqa: D401
        pass

    curve_generator_mod.CurveGenerator = CurveGenerator  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.core.curve_generator", curve_generator_mod)

    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: config,
        configure_container_impl=fake_configure_container,
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )

    assert main_mod.test_core_only() == 0


def test_import_on_win32_sets_utf8_io_env_and_sys_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32", raising=False)
    monkeypatch.delenv("PYTHONIOENCODING", raising=False)

    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: SimpleNamespace(),
        configure_container_impl=lambda *, config: _DummyContainer(),
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )

    assert os.environ.get("PYTHONIOENCODING") == "utf-8"
    assert str(main_mod.PROJECT_ROOT) in sys.path


def test_install_global_exception_hooks_sets_sys_and_thread_hooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: SimpleNamespace(),
        configure_container_impl=lambda *, config: _DummyContainer(),
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )

    main_mod._install_global_exception_hooks()
    assert callable(sys.excepthook)
    assert hasattr(threading, "excepthook")
    assert callable(threading.excepthook)  # type: ignore[arg-type]


def test_main_win32_taskbar_app_id_and_abouttoquit_connect_failure_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32", raising=False)
    _install_fake_qt_modules(monkeypatch)
    _install_fake_ui_modules(monkeypatch)

    class _BadSignal:
        def connect(self, _fn):  # noqa: ANN001
            raise RuntimeError("nope")

    class _WinApp(_DummyApp):
        def __init__(self, argv):  # noqa: ANN001
            super().__init__(argv)
            self.aboutToQuit = _BadSignal()

    from PySide6 import QtWidgets as qtwidgets  # type: ignore

    qtwidgets.QApplication = _WinApp  # type: ignore[attr-defined]

    called: list[str] = []

    ctypes_mod = ModuleType("ctypes")
    ctypes_mod.windll = SimpleNamespace(
        shell32=SimpleNamespace(
            SetCurrentProcessExplicitAppUserModelID=lambda _appid: called.append("appid")
        )
    )
    monkeypatch.setitem(sys.modules, "ctypes", ctypes_mod)

    config = SimpleNamespace(
        app=SimpleNamespace(environment="test", debug=False),
        paths=SimpleNamespace(logs="logs"),
        log=SimpleNamespace(file="app.log", level="INFO", max_size=1, backup_count=1),
    )

    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: config,
        configure_container_impl=lambda *, config: _DummyContainer(),
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )

    assert main_mod.main() == 42
    assert called == ["appid"]


def test_main_win32_app_id_exception_is_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32", raising=False)
    _install_fake_qt_modules(monkeypatch)
    _install_fake_ui_modules(monkeypatch)

    ctypes_mod = ModuleType("ctypes")
    ctypes_mod.windll = SimpleNamespace(
        shell32=SimpleNamespace(
            SetCurrentProcessExplicitAppUserModelID=lambda _appid: (_ for _ in ()).throw(
                RuntimeError("boom")
            )
        )
    )
    monkeypatch.setitem(sys.modules, "ctypes", ctypes_mod)

    config = SimpleNamespace(
        app=SimpleNamespace(environment="test", debug=False),
        paths=SimpleNamespace(logs="logs"),
        log=SimpleNamespace(file="app.log", level="INFO", max_size=1, backup_count=1),
    )

    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: config,
        configure_container_impl=lambda *, config: _DummyContainer(),
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )
    assert main_mod.main() == 42


def test_cleanup_shutdown_exception_is_swallowed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake_qt_modules(monkeypatch)
    _install_fake_ui_modules(monkeypatch)

    config = SimpleNamespace(
        app=SimpleNamespace(environment="test", debug=False),
        paths=SimpleNamespace(logs="logs"),
        log=SimpleNamespace(file="app.log", level="INFO", max_size=1, backup_count=1),
    )

    registered: list[object] = []
    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: config,
        configure_container_impl=lambda *, config: _DummyContainer(),
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )
    monkeypatch.setattr(main_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(main_mod.atexit, "register", lambda fn: registered.append(fn))
    monkeypatch.setattr(main_mod.logging, "shutdown", lambda: (_ for _ in ()).throw(RuntimeError("x")))

    assert main_mod.main() == 42
    assert registered
    registered[0]()  # should not raise


def test_test_core_only_returns_1_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(app=SimpleNamespace(name="X", version="1.0"))

    class _CoreContainer(_DummyContainer):
        def resolve(self, _cls):  # noqa: ANN001
            raise RuntimeError("boom")

    main_mod = _import_main_with_core_stubs(
        monkeypatch,
        get_config_impl=lambda: config,
        configure_container_impl=lambda *, config: _CoreContainer(),
        ensure_secure_startup_impl=lambda *, config: None,
        setup_logger_impl=lambda *a, **k: None,
    )

    assert main_mod.test_core_only() == 1
