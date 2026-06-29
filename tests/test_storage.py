"""Tests for enpaf.core.storage — SQLite key/value store and collections."""

import pytest


# ─── Key/value store ──────────────────────────────────────────

def test_set_and_get_string(storage):
    storage.set("theme", "dark")
    assert storage.get("theme") == "dark"


def test_get_missing_returns_default(storage):
    assert storage.get("missing") is None
    assert storage.get("missing", "fallback") == "fallback"


@pytest.mark.parametrize(
    "value",
    [42, 3.14, True, False, None, "hello", {"a": 1, "b": [1, 2]}, [1, "two", 3.0]],
)
def test_roundtrip_types_preserved(storage, value):
    storage.set("k", value)
    assert storage.get("k") == value


def test_set_overwrites_existing_key(storage):
    storage.set("k", "first")
    storage.set("k", "second")
    assert storage.get("k") == "second"


def test_exists(storage):
    assert storage.exists("k") is False
    storage.set("k", 1)
    assert storage.exists("k") is True


def test_delete_returns_whether_existed(storage):
    storage.set("k", 1)
    assert storage.delete("k") is True
    assert storage.delete("k") is False
    assert storage.exists("k") is False


def test_keys_and_pattern(storage):
    storage.set("user:1", "a")
    storage.set("user:2", "b")
    storage.set("config", "c")
    assert set(storage.keys()) == {"user:1", "user:2", "config"}
    assert set(storage.keys("user:%")) == {"user:1", "user:2"}


def test_all_and_clear(storage):
    storage.set("a", 1)
    storage.set("b", "two")
    assert storage.all() == {"a": 1, "b": "two"}
    storage.clear()
    assert storage.all() == {}


def test_unicode_values(storage):
    storage.set("greeting", "Привет, мир! 👋")
    assert storage.get("greeting") == "Привет, мир! 👋"


# ─── Collections ──────────────────────────────────────────────

def test_collection_add_assigns_incrementing_ids(storage):
    notes = storage.collection("notes")
    id1 = notes.add({"text": "one"})
    id2 = notes.add({"text": "two"})
    assert id1 != id2
    assert isinstance(id1, int)


def test_collection_all_includes_metadata(storage):
    notes = storage.collection("notes")
    notes.add({"text": "hi"})
    docs = notes.all()
    assert len(docs) == 1
    assert docs[0]["text"] == "hi"
    assert "_id" in docs[0]
    assert "_created_at" in docs[0]


def test_collection_find_and_find_one(storage):
    users = storage.collection("users")
    users.add({"name": "Alex", "age": 25})
    users.add({"name": "Sam", "age": 25})
    users.add({"name": "Alex", "age": 30})
    assert len(users.find({"name": "Alex"})) == 2
    assert len(users.find({"age": 25})) == 2
    assert users.find_one({"name": "Sam"})["age"] == 25
    assert users.find_one({"name": "Nobody"}) is None


def test_collection_update(storage):
    todos = storage.collection("todos")
    doc_id = todos.add({"task": "write tests", "done": False})
    assert todos.update(doc_id, {"task": "write tests", "done": True}) is True
    assert todos.find_one({"task": "write tests"})["done"] is True
    assert todos.update(99999, {"x": 1}) is False


def test_collection_delete_and_count(storage):
    c = storage.collection("items")
    a = c.add({"v": 1})
    c.add({"v": 2})
    assert c.count() == 2
    assert c.delete(a) is True
    assert c.count() == 1


def test_collection_clear_is_scoped(storage):
    storage.collection("keep").add({"v": 1})
    drop = storage.collection("drop")
    drop.add({"v": 1})
    drop.clear()
    assert drop.count() == 0
    assert storage.collection("keep").count() == 1


def test_collections_are_isolated(storage):
    storage.collection("a").add({"v": 1})
    storage.collection("b").add({"v": 2})
    assert storage.collection("a").count() == 1
    assert storage.collection("b").count() == 1
