import json

from modules.state import load_id_map, save_id_map
from modules import state
import pytest


class StateResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


class StateConnection:
    def __init__(self, stored=None, existing=True, history=False):
        self.stored = stored
        self.existing = existing
        self.history = history
        self.statements = []

    def execute(self, statement, parameters=None):
        query = str(statement)
        self.statements.append((query, parameters))
        if "SELECT id_map" in query:
            value = self.stored
        elif "to_regclass('public.tb_rpa_state')" in query:
            value = 'tb_rpa_state' if self.existing else None
        elif "to_regclass('public.tb_log_rpa')" in query:
            value = 'tb_log_rpa'
        elif "SELECT EXISTS" in query:
            value = self.history
        else:
            value = None
        return StateResult(value)


def test_database_map_ignores_invalid_local_cache(monkeypatch):
    connection = StateConnection(stored={"tb_address": {"5": 50}})
    monkeypatch.setattr(state, "load_id_map", lambda: (_ for _ in ()).throw(AssertionError("cache must not be read")))
    assert state.load_database_id_map(connection) == {"tb_address": {5: 50}}
    assert not any("CREATE TABLE" in query for query, _ in connection.statements)


def test_first_activation_imports_existing_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_id_map({"tb_address": {5: 50}})
    connection = StateConnection(existing=False, history=True)
    assert state.load_database_id_map(connection) == {"tb_address": {5: 50}}
    assert any("CREATE TABLE" in query for query, _ in connection.statements)


def test_missing_bootstrap_state_refuses_previous_executions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="execuções anteriores"):
        state.load_database_id_map(StateConnection(history=True))


def test_existing_empty_json_can_bootstrap_after_an_empty_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_id_map({})
    assert state.load_database_id_map(StateConnection(history=True)) == {}


def test_database_state_is_serialized_with_bound_parameters():
    connection = StateConnection()
    state.save_database_id_map(connection, {"tb_address": {5: 50}})
    query, parameters = connection.statements[-1]
    assert "ON CONFLICT" in query
    assert json.loads(parameters['id_map']) == {"tb_address": {"5": 50}}


def test_load_returns_empty_dict_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert load_id_map() == {}


def test_save_then_load_round_trips_with_int_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    id_map = {
        "tb_user": {1: 10, 2: 11},
        "tb_address": {5: 50},
    }

    save_id_map(id_map)

    loaded = load_id_map()

    assert loaded == id_map
    # As chaves do legado precisam voltar como inteiro, não como texto.
    assert all(
        isinstance(legacy_id, int)
        for mapping in loaded.values()
        for legacy_id in mapping
    )


def test_saved_file_is_valid_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    save_id_map({"tb_user": {1: 10}})

    content = (tmp_path / "state" / "id_map.json").read_text(encoding="utf-8")

    assert json.loads(content) == {"tb_user": {"1": 10}}
