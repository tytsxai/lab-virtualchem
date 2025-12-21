from __future__ import annotations

from pathlib import Path

import pytest

from src.models.experiment import Experiment


def _make_experiment_with_xss_payload() -> Experiment:
    exp = Experiment(experiment_type="titration", title="normal")
    exp.prepare()
    exp.start()
    exp.complete()
    return exp


@pytest.mark.unit
def test_html_report_escapes_xss_payloads():
    exp = _make_experiment_with_xss_payload()

    payload = '<img src=x onerror="alert(1)"><script>alert(1)</script>'
    exp.title = payload
    exp.state = payload
    exp.record_data(payload, payload)
    exp.record_observation(payload)

    html_report = exp.export_report(format="html")

    assert payload not in html_report
    assert "&lt;img" in html_report
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_report


@pytest.mark.unit
def test_markdown_report_escapes_markdown_special_chars():
    exp = _make_experiment_with_xss_payload()

    payload = "name|value *bold* _italic_ [link](x) `code`"
    exp.title = payload
    exp.record_data("k|1", payload)

    md_report = exp.export_report(format="markdown")

    assert payload not in md_report
    assert "\\|" in md_report
    assert "\\*" in md_report
    assert "\\_" in md_report
    assert "\\[" in md_report
    assert "\\]" in md_report
    assert "\\(" in md_report
    assert "\\)" in md_report
    assert "\\`" in md_report


@pytest.mark.unit
def test_save_report_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    exp = _make_experiment_with_xss_payload()

    with pytest.raises(ValueError):
        exp.save_report(Path("../evil.json"), format="json")

    with pytest.raises(ValueError):
        exp.save_report(Path("data/reports/../evil.json"), format="json")


@pytest.mark.unit
def test_save_report_rejects_absolute_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    exp = _make_experiment_with_xss_payload()

    with pytest.raises(ValueError):
        exp.save_report(Path("/tmp/evil.json"), format="json")


@pytest.mark.unit
def test_save_report_writes_under_controlled_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    exp = _make_experiment_with_xss_payload()

    saved_path = exp.save_report(Path("nested/report.json"), format="json")
    assert saved_path == (tmp_path / "data" / "reports" / "nested" / "report.json")
    assert saved_path.exists()

