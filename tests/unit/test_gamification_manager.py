from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from src.gamification.achievement_system import UserAchievement
from src.gamification.gamification_manager import GamificationManager
from src.models.user_record import Mistake, StepRecord, UserRecord
from src.storage.json_store import JSONStore


def _make_completed_record(
    *,
    user_id: str,
    experiment_id: str,
    record_id: str = "r1",
    score_total: int = 80,
    duration_seconds: int = 120,
    mistakes: int = 0,
) -> UserRecord:
    started_at = datetime.now() - timedelta(seconds=duration_seconds)
    completed_at = datetime.now()

    step_records: list[StepRecord] = []
    step_mistakes = [
        Mistake(step_id="s1", error_type="test_error", description="oops")
        for _ in range(mistakes)
    ]
    step_records.append(
        StepRecord(
            step_id="s1",
            started_at=started_at,
            completed_at=completed_at,
            passed=True,
            mistakes=step_mistakes,
        )
    )

    record = UserRecord(
        record_id=record_id,
        user_id=user_id,
        experiment_id=experiment_id,
        experiment_title="Test Experiment",
        started_at=started_at,
        completed_at=completed_at,
        status="completed",
        step_records=step_records,
    )
    record.score.total = score_total
    return record


@pytest.mark.unit
def test_on_experiment_completed_unlocks_achievements_and_adds_exp_reward(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("GAMIFICATION_HMAC_SECRET", "test-secret")
    store = JSONStore(base_dir=str(tmp_path / "records"))
    manager = GamificationManager(storage=store)

    user_id = "u_achievements"
    experiment_id = "exp_achievements"
    record = _make_completed_record(
        user_id=user_id,
        experiment_id=experiment_id,
        score_total=100,
        duration_seconds=600,  # 避免触发快速完成 1.1 倍
        mistakes=0,
    )
    assert store.save_record(record)

    result = manager.on_experiment_completed(user_id=user_id, experiment_id=experiment_id)

    base_exp = int(int(100) * 1.2)  # 零失误额外 20%
    expected_achievement_exp = 50 + 100 + 120  # 首次尝试 + 完美实验 + 零失误
    assert result["exp_gained"] == base_exp + expected_achievement_exp

    unlocked_ids = {a.id for a in result["new_achievements"]}
    assert {"first_experiment", "perfect_score", "no_mistakes"} <= unlocked_ids

    reloaded = manager.get_or_create_user_data(user_id)
    assert {a.achievement_id for a in reloaded.achievements if a.completed} >= {
        "first_experiment",
        "perfect_score",
        "no_mistakes",
    }
    assert reloaded.level.total_exp == result["exp_gained"]


@pytest.mark.unit
def test_on_experiment_completed_level_up_without_new_achievements(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMIFICATION_HMAC_SECRET", "test-secret")
    store = JSONStore(base_dir=str(tmp_path / "records"))
    manager = GamificationManager(storage=store)

    user_id = "u_levelup"
    experiment_id = "exp_levelup"

    data = manager.get_or_create_user_data(user_id)
    for achievement_id in manager.achievement_manager.achievements:
        data.achievements.append(
            UserAchievement(
                achievement_id=achievement_id,
                user_id=user_id,
                progress=100.0,
                completed=True,
            )
        )
    # 预置经验值到临界点附近，确保本次结算触发升级（分数本身上限为 100）
    data.level.exp = 140
    data.level.total_exp = 140
    manager.save_user_data(data)

    record = _make_completed_record(
        user_id=user_id,
        experiment_id=experiment_id,
        score_total=10,
        duration_seconds=600,
        mistakes=1,
    )
    assert store.save_record(record)

    result = manager.on_experiment_completed(user_id=user_id, experiment_id=experiment_id)
    assert result["new_achievements"] == []
    assert result["exp_gained"] == 10
    assert result["level_up"] is True
    assert result["level_info"]["old_level"] == 1
    assert result["level_info"]["new_level"] >= 2


@pytest.mark.unit
def test_on_experiment_completed_completes_daily_quest(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMIFICATION_HMAC_SECRET", "test-secret")
    store = JSONStore(base_dir=str(tmp_path / "records"))
    manager = GamificationManager(storage=store)

    user_id = "u_quest"
    experiment_id = "exp_quest"
    record = _make_completed_record(
        user_id=user_id,
        experiment_id=experiment_id,
        score_total=10,
        duration_seconds=600,
        mistakes=1,
    )
    assert store.save_record(record)

    result = manager.on_experiment_completed(user_id=user_id, experiment_id=experiment_id)
    completed_ids = {q.id for q in result["completed_quests"]}
    assert "daily_complete_1" in completed_ids


@pytest.mark.unit
def test_get_or_create_user_data_accepts_missing_signature(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMIFICATION_HMAC_SECRET", "test-secret")
    store = JSONStore(base_dir=str(tmp_path / "records"))
    manager = GamificationManager(storage=store)

    user_id = "u_signature_missing"
    data = manager.get_or_create_user_data(user_id)
    data.stats.total_score = 123
    manager.save_user_data(data)

    config_path = tmp_path / "records" / "config.json"
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    raw[f"gamification/{user_id}"].pop("integrity_signature", None)
    config_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    reloaded = manager.get_or_create_user_data(user_id)
    assert reloaded.stats.total_score == 123


@pytest.mark.unit
def test_get_or_create_user_data_recovers_from_invalid_payload_type(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMIFICATION_HMAC_SECRET", "test-secret")
    store = JSONStore(base_dir=str(tmp_path / "records"))
    manager = GamificationManager(storage=store)

    user_id = "u_bad_payload"
    store.set(f"gamification/{user_id}", ["not", "a", "dict"])

    data = manager.get_or_create_user_data(user_id)
    assert data.user_id == user_id
    assert data.level.level == 1
    assert data.stats.experiments_completed == 0


@pytest.mark.unit
def test_on_experiment_completed_validates_inputs_and_requires_completed_record(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("GAMIFICATION_HMAC_SECRET", "test-secret")
    store = JSONStore(base_dir=str(tmp_path / "records"))
    manager = GamificationManager(storage=store)

    with pytest.raises(ValueError, match="experiment_id is required"):
        manager.on_experiment_completed(user_id="u", experiment_id="")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="no completed record found"):
        manager.on_experiment_completed(user_id="u", experiment_id="missing_exp")


@pytest.mark.unit
def test_get_hmac_secret_prefers_fallbacks(monkeypatch):
    monkeypatch.delenv("GAMIFICATION_HMAC_SECRET", raising=False)
    monkeypatch.setenv("SESSION_SECRET_KEY", "session-secret")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    assert GamificationManager._get_hmac_secret() == b"session-secret"


@pytest.mark.unit
def test_update_stats_daily_streak_and_special_time(tmp_path, monkeypatch):
    from src.gamification import gamification_manager as gm

    class _FakeDateTime(datetime):
        _now = datetime(2025, 1, 2, 0, 1, 2)

        @classmethod
        def now(cls):  # noqa: D102
            return cls._now

        @classmethod
        def strptime(cls, date_string: str, fmt: str):  # noqa: D102
            return datetime.strptime(date_string, fmt)

    stats = gm.UserStats(user_id="u_stats")
    stats.last_activity_date = "2025-01-01"
    stats.daily_streak = 2

    monkeypatch.setattr(gm, "datetime", _FakeDateTime)
    manager = gm.GamificationManager(storage=JSONStore(base_dir=str(tmp_path / "records")))
    manager._update_stats_on_experiment(stats, score=0, duration_seconds=10, mistake_count=1)

    assert stats.daily_streak == 3
    assert stats.last_activity_date == "2025-01-02"
    assert stats.midnight_experiment == 1

    _FakeDateTime._now = datetime(2025, 1, 2, 3, 0, 0)
    manager._update_stats_on_experiment(stats, score=0, duration_seconds=10, mistake_count=1)
    assert stats.early_morning_experiment == 1
