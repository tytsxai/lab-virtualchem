from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from src.gamification.gamification_manager import GamificationManager
from src.gamification.quest_system import QuestStatus
from src.gamification.level_system import LevelSystem
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
    if mistakes:
        step_records.append(
            StepRecord(
                step_id="s1",
                started_at=started_at,
                completed_at=completed_at,
                passed=True,
                mistakes=[
                    Mistake(
                        step_id="s1",
                        error_type="test_error",
                        description="oops",
                    )
                    for _ in range(mistakes)
                ],
            )
        )
    else:
        step_records.append(
            StepRecord(
                step_id="s1",
                started_at=started_at,
                completed_at=completed_at,
                passed=True,
                mistakes=[],
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
def test_on_experiment_completed_uses_record_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMIFICATION_HMAC_SECRET", "test-secret")
    store = JSONStore(base_dir=str(tmp_path / "records"))
    manager = GamificationManager(storage=store)

    user_id = "u1"
    experiment_id = "exp1"
    record = _make_completed_record(
        user_id=user_id,
        experiment_id=experiment_id,
        score_total=90,
        duration_seconds=100,
        mistakes=0,
    )
    assert store.save_record(record)

    result1 = manager.on_experiment_completed(user_id=user_id, experiment_id=experiment_id)
    assert result1["already_settled"] is False

    expected_base_exp = int(int(90) * 1.2)
    expected_base_exp = int(expected_base_exp * 1.1)
    achievement_exp = sum(getattr(a, "exp_reward", 0) for a in result1["new_achievements"])
    assert result1["exp_gained"] == expected_base_exp + achievement_exp

    data_after = manager.get_or_create_user_data(user_id)
    assert data_after.stats.experiments_completed == 1
    assert experiment_id in set(data_after.stats.settled_experiment_ids)

    result2 = manager.on_experiment_completed(user_id=user_id, experiment_id=experiment_id)
    assert result2["already_settled"] is True
    assert result2["exp_gained"] == 0

    data_after2 = manager.get_or_create_user_data(user_id)
    assert data_after2.stats.experiments_completed == 1


@pytest.mark.unit
def test_gamification_data_hmac_tamper_is_detected(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMIFICATION_HMAC_SECRET", "test-secret")
    store = JSONStore(base_dir=str(tmp_path / "records"))
    manager = GamificationManager(storage=store)

    user_id = "u2"
    data = manager.get_or_create_user_data(user_id)
    data.stats.total_score = 123
    manager.save_user_data(data)

    config_path = (tmp_path / "records" / "config.json")
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    raw[f"gamification/{user_id}"]["stats"]["total_score"] = 999999
    config_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    reloaded = manager.get_or_create_user_data(user_id)
    assert reloaded.stats.total_score == 0
    assert reloaded.level.total_exp == 0


@pytest.mark.unit
def test_claim_quest_reward_optimistic_lock(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMIFICATION_HMAC_SECRET", "test-secret")
    store = JSONStore(base_dir=str(tmp_path / "records"))
    manager = GamificationManager(storage=store)

    user_id = "u3"
    data = manager.get_or_create_user_data(user_id)
    quest = next(q for q in data.quests if q.quest_id == "daily_complete_1")
    quest.status = QuestStatus.COMPLETED
    quest.progress = quest.target
    quest.version = 0
    manager.save_user_data(data)

    r1 = manager.claim_quest_reward(user_id=user_id, quest_id=quest.quest_id, expected_version=0)
    assert r1["success"] is True
    assert r1["exp_gained"] > 0

    r2 = manager.claim_quest_reward(user_id=user_id, quest_id=quest.quest_id, expected_version=0)
    assert r2["success"] is False
    assert r2["version_conflict"] is True

    r3 = manager.claim_quest_reward(user_id=user_id, quest_id=quest.quest_id)
    assert r3["success"] is False
    assert r3["exp_gained"] == 0


@pytest.mark.unit
def test_level_system_add_exp_rejects_negative():
    system = LevelSystem()
    level = system.create_user_level("u4")
    with pytest.raises(ValueError):
        system.add_exp(level, -1)
