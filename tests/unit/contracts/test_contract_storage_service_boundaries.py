from __future__ import annotations

from dataclasses import dataclass

from src.contracts.storage_service import (
    DeleteRequest,
    InMemoryStorageService,
    QueryFilter,
    QueryOperator,
    QueryRequest,
    SaveRequest,
)


@dataclass
class _Obj:
    id: str
    age: int | str
    name: str = "Alice"


@dataclass
class _RecordObj:
    record_id: str


def test_inmemory_storage_save_overwrite_false_rejects_existing_id() -> None:
    service = InMemoryStorageService()

    first = service.save(SaveRequest(entity_type="person", entity=_Obj(id="1", age=1)))
    assert first.success

    second = service.save(
        SaveRequest(entity_type="person", entity=_Obj(id="1", age=1), overwrite=False)
    )
    assert not second.success
    assert second.entity_id == "1"
    assert "不允许覆盖" in second.message


def test_inmemory_storage_resolve_id_supports_object_id_and_record_id() -> None:
    service = InMemoryStorageService()

    obj = _Obj(id="abc", age=10)
    resp = service.save(SaveRequest(entity_type="obj", entity=obj))
    assert resp.success
    assert resp.entity_id == "abc"

    record_entity = _RecordObj(record_id="rec-1")
    resp2 = service.save(SaveRequest(entity_type="rec", entity=record_entity))
    assert resp2.success
    assert resp2.entity_id == "rec-1"


def test_inmemory_storage_query_supports_object_fields_and_sort_desc() -> None:
    service = InMemoryStorageService()
    service.save(SaveRequest(entity_type="obj", entity=_Obj(id="1", age=2, name="b")))
    service.save(SaveRequest(entity_type="obj", entity=_Obj(id="2", age=1, name="a")))

    response = service.query(
        QueryRequest(entity_type="obj", sort_by="age", sort_order="desc")
    )
    assert response.success
    assert [item.id for item in response.data] == ["1", "2"]


def test_inmemory_storage_query_filters_cover_in_like_between_and_comparisons() -> None:
    service = InMemoryStorageService()
    service.save(SaveRequest(entity_type="t", entity={"id": "1", "age": 10, "tag": "X"}))
    service.save(SaveRequest(entity_type="t", entity={"id": "2", "age": 20, "tag": "y"}))
    service.save(SaveRequest(entity_type="t", entity={"id": "3", "age": "n/a"}))

    resp_in = service.query(
        QueryRequest(
            entity_type="t",
            filters=[QueryFilter(field="tag", operator=QueryOperator.IN, value={"X"})],
        )
    )
    assert [item["id"] for item in resp_in.data] == ["1"]

    resp_in_bad_expected = service.query(
        QueryRequest(
            entity_type="t",
            filters=[
                QueryFilter(field="tag", operator=QueryOperator.IN, value="not-a-seq")
            ],
        )
    )
    assert resp_in_bad_expected.data == []

    resp_like = service.query(
        QueryRequest(
            entity_type="t",
            filters=[QueryFilter(field="tag", operator=QueryOperator.LIKE, value="x")],
        )
    )
    assert [item["id"] for item in resp_like.data] == ["1"]

    resp_between = service.query(
        QueryRequest(
            entity_type="t",
            filters=[
                QueryFilter(field="age", operator=QueryOperator.BETWEEN, value=(9, 10))
            ],
        )
    )
    assert [item["id"] for item in resp_between.data] == ["1"]

    resp_between_invalid_length = service.query(
        QueryRequest(
            entity_type="t",
            filters=[
                QueryFilter(field="age", operator=QueryOperator.BETWEEN, value=(1, 2, 3))
            ],
        )
    )
    assert resp_between_invalid_length.data == []

    resp_between_typeerror = service.query(
        QueryRequest(
            entity_type="t",
            filters=[
                QueryFilter(field="age", operator=QueryOperator.BETWEEN, value=(1, 2))
            ],
        )
    )
    assert resp_between_typeerror.data == []

    resp_ne = service.query(
        QueryRequest(
            entity_type="t",
            filters=[QueryFilter(field="tag", operator=QueryOperator.NE, value="X")],
        )
    )
    assert {item["id"] for item in resp_ne.data} == {"2", "3"}


def test_inmemory_storage_delete_missing_returns_failure() -> None:
    service = InMemoryStorageService()
    response = service.delete(DeleteRequest(entity_type="t", entity_id="missing"))
    assert not response.success
    assert response.deleted_count == 0


def test_inmemory_storage_count_and_exists_use_filters() -> None:
    service = InMemoryStorageService()
    r1 = service.save(SaveRequest(entity_type="t", entity=_Obj(id="1", age=1)))
    r2 = service.save(SaveRequest(entity_type="t", entity=_Obj(id="2", age=2)))
    assert r1.entity_id == "1"
    assert r2.entity_id == "2"

    assert service.exists("t", "1") is True
    assert service.exists("t", "nope") is False

    assert service.count("t") == 2
    assert (
        service.count(
            "t", filters=[QueryFilter(field="age", operator=QueryOperator.GTE, value=2)]
        )
        == 1
    )
