import logging

import pandas as pd
import pytest

from modules import load


class FakeTransaction:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.committed = exc_type is None
        self.rolled_back = exc_type is not None
        return False


class FakeConnection:
    def __init__(self):
        self.transaction = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def begin(self):
        self.transaction = FakeTransaction()
        return self.transaction


class FakeEngine:
    def __init__(self):
        self.connection = FakeConnection()

    def connect(self):
        return self.connection


def test_load_data_saves_id_map_only_after_transaction_commits(monkeypatch):
    engine = FakeEngine()
    id_map = {"tb_user": {1: 100}}
    saved = []
    monkeypatch.setattr(load, "get_logger", lambda: logging.getLogger("load-test"))
    monkeypatch.setattr(load, "load_id_map", lambda: id_map)
    monkeypatch.setattr(load, "create_second_year_connection", lambda: engine)
    monkeypatch.setattr(load, "_apply_deletions", lambda *args: None)

    def apply_upserts(connection, dataframes, mapping, counts):
        assert connection is engine.connection
        mapping["tb_user"][2] = 101
        counts["tb_user"] = {"inserted": 1, "updated": 0, "deleted": 0}

    monkeypatch.setattr(load, "_apply_upserts", apply_upserts)
    monkeypatch.setattr(
        load,
        "save_id_map",
        lambda mapping: saved.append(
            (mapping.copy(), engine.connection.transaction.committed)
        ),
    )
    monkeypatch.setattr(load, "log_commit", lambda logger: None)

    result = load.load_data(
        {"tb_user": pd.DataFrame({"id": [2], "email": ["new@test"]})},
        {"tb_user": {1, 2}},
    )

    assert result == {"tb_user": {"inserted": 1, "updated": 0, "deleted": 0}}
    assert engine.connection.transaction.committed is True
    assert engine.connection.transaction.rolled_back is False
    assert saved == [({"tb_user": {1: 100, 2: 101}}, True)]


def test_load_data_rolls_back_and_does_not_save_id_map_on_failure(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(load, "get_logger", lambda: logging.getLogger("load-test"))
    monkeypatch.setattr(load, "load_id_map", lambda: {"tb_user": {1: 100}})
    monkeypatch.setattr(load, "create_second_year_connection", lambda: engine)
    monkeypatch.setattr(load, "_apply_deletions", lambda *args: None)
    monkeypatch.setattr(
        load, "_apply_upserts", lambda *args: (_ for _ in ()).throw(RuntimeError("write failed"))
    )
    saved = []
    rollback_logs = []
    monkeypatch.setattr(load, "save_id_map", lambda mapping: saved.append(mapping))
    monkeypatch.setattr(load, "log_rollback", lambda logger: rollback_logs.append(True))

    with pytest.raises(RuntimeError, match="write failed"):
        load.load_data({}, {"tb_user": {1}})

    assert engine.connection.transaction.committed is False
    assert engine.connection.transaction.rolled_back is True
    assert saved == []
    assert rollback_logs == [True]


def test_foreign_keys_are_translated_when_a_reference_map_exists():
    source = pd.DataFrame(
        {"id": [7], "user_id": [1], "property_id": [8]}
    )

    result = load._replace_foreign_keys(
        "tb_user_property",
        source,
        {"tb_user": {1: 101}},
    )

    assert result["user_id"].tolist() == [101]
    assert result["property_id"].tolist() == [8]
    assert source["user_id"].tolist() == [1]
