from __future__ import annotations

from typing import Any

from src.contracts.storage_service import (
    DeleteRequest,
    QueryFilter,
    QueryOperator,
    QueryRequest,
    SaveRequest,
)
from src.services.storage_service_impl import StorageServiceImpl


class _MemoryStorage:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def save(self, key: str, value: Any, metadata: dict | None = None) -> bool:
        self._data[key] = value
        return True

    def load(self, key: str) -> Any | None:
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    def exists(self, key: str) -> bool:
        return key in self._data

    def list_keys(self, prefix: str | None = None) -> list[str]:
        if prefix is None:
            return list(self._data.keys())
        return [k for k in self._data if k.startswith(prefix)]


def test_storage_service_save_and_get_by_id_and_exists_and_close():
    storage = _MemoryStorage()
    service = StorageServiceImpl(storage)

    entity = {"id": "e1", "name": "alice", "score": 10}
    resp = service.save(SaveRequest(entity=entity, entity_type="users"))
    assert resp.success is True
    assert resp.entity_id is not None
    assert resp.entity_id.startswith("users/")

    # get_by_id uses entity_id suffix only
    storage.save("users/e1", entity)
    assert service.get_by_id("users", "e1") == entity
    assert service.exists("users", "e1") is True

    with service:
        pass
    assert storage.closed is True


def test_storage_service_query_filters_sort_pagination():
    storage = _MemoryStorage()
    service = StorageServiceImpl(storage)

    storage.save("items/1", {"id": "1", "name": "alpha", "score": 10})
    storage.save("items/2", {"id": "2", "name": "beta", "score": 20})
    storage.save("items/3", {"id": "3", "name": "alphabet", "score": 15})

    req = QueryRequest(
        entity_type="items",
        filters=[
            QueryFilter(field="name", operator=QueryOperator.LIKE, value="alp"),
            QueryFilter(field="score", operator=QueryOperator.GTE, value=10),
        ],
        sort_by="score",
        sort_order="desc",
        limit=1,
        offset=0,
    )
    resp = service.query(req)
    assert resp.success is True
    assert resp.total_count == 2
    assert resp.has_more is True
    assert resp.data[0]["id"] in {"3", "1"}
    assert resp.data[0]["score"] == 15

    # second page
    req2 = QueryRequest(
        entity_type="items",
        filters=req.filters,
        sort_by="score",
        sort_order="desc",
        limit=1,
        offset=1,
    )
    resp2 = service.query(req2)
    assert resp2.success is True
    assert resp2.has_more is False
    assert resp2.data[0]["id"] == "1"


def test_storage_service_delete_hard_and_soft():
    storage = _MemoryStorage()
    service = StorageServiceImpl(storage)
    storage.save("items/1", {"id": "1", "name": "alpha"})

    hard = service.delete(DeleteRequest(entity_type="items", entity_id="1"))
    assert hard.success is True
    assert hard.deleted_count == 1
    assert storage.exists("items/1") is False

    storage.save("items/2", {"id": "2", "name": "beta"})
    soft = service.delete(
        DeleteRequest(entity_type="items", entity_id="2", soft_delete=True)
    )
    assert soft.success is True
    assert soft.deleted_count == 1
    assert storage.load("items/2")["_deleted"] is True


def test_storage_service_count_and_batch_ops():
    class _Obj:
        def __init__(self, id: str, name: str, score: int) -> None:
            self.id = id
            self.name = name
            self.score = score

    storage = _MemoryStorage()
    service = StorageServiceImpl(storage)

    requests = [
        SaveRequest(entity=_Obj("1", "a", 1), entity_type="items"),
        SaveRequest(entity=_Obj("2", "b", 2), entity_type="items"),
    ]
    responses = service.batch_save(requests)
    assert all(r.success for r in responses)

    # count without filters
    assert service.count("items") == 2

    # count with filters
    filters = [QueryFilter(field="score", operator=QueryOperator.GT, value=1)]
    assert service.count("items", filters=filters) == 1

    del_resps = service.batch_delete(
        [
            DeleteRequest(entity_type="items", entity_id="1"),
            DeleteRequest(entity_type="items", entity_id="nope"),
        ]
    )
    assert del_resps[0].success is True
    assert del_resps[1].success is False or del_resps[1].deleted_count in (0, 1)


def test_storage_service_query_handles_underlying_errors():
    class _BrokenStorage(_MemoryStorage):
        def list_keys(self, prefix: str | None = None) -> list[str]:
            raise RuntimeError("boom")

    service = StorageServiceImpl(_BrokenStorage())
    resp = service.query(QueryRequest(entity_type="items"))
    assert resp.success is False


def test_storage_service_save_handles_underlying_errors():
    class _BrokenStorage(_MemoryStorage):
        def save(self, key: str, value: Any, metadata: dict | None = None) -> bool:
            raise RuntimeError("boom")

    service = StorageServiceImpl(_BrokenStorage())
    resp = service.save(SaveRequest(entity={"id": "x"}, entity_type="items"))
    assert resp.success is False
    assert resp.errors


def test_storage_service_filters_cover_comparisons_and_in_and_ne():
    storage = _MemoryStorage()
    service = StorageServiceImpl(storage)

    storage.save("items/1", {"id": "1", "n": 1, "tag": "a"})
    storage.save("items/2", {"id": "2", "n": 2, "tag": "b"})
    storage.save("items/3", {"id": "3", "n": 3, "tag": "c"})

    req = QueryRequest(
        entity_type="items",
        filters=[
            QueryFilter(field="n", operator=QueryOperator.LT, value=3),
            QueryFilter(field="n", operator=QueryOperator.NE, value=1),
            QueryFilter(field="tag", operator=QueryOperator.IN, value=["b", "z"]),
        ],
    )
    resp = service.query(req)
    assert resp.success is True
    assert [e["id"] for e in resp.data] == ["2"]


def test_storage_service_close_is_idempotent_and_swallow_close_errors_and_save_false():
    class _CloseBoomStorage(_MemoryStorage):
        def __init__(self) -> None:
            super().__init__()
            self.close_calls = 0

        def close(self) -> None:
            self.close_calls += 1
            raise RuntimeError("boom")

        def save(self, key: str, value: Any, metadata: dict | None = None) -> bool:  # noqa: ARG002
            self._data[key] = value
            return False

    storage = _CloseBoomStorage()
    service = StorageServiceImpl(storage)
    resp = service.save(SaveRequest(entity={"x": 1}, entity_type="items"))
    assert resp.success is False
    assert resp.message == "保存失败"

    service.close()
    service.close()
    assert storage.close_calls == 1
