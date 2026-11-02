import os

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from modules import load, state


@pytest.fixture
def database(tmp_path, monkeypatch):
    url = os.getenv("RPA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("RPA_TEST_DATABASE_URL aponta para o PostgreSQL local descartável")
    parsed = make_url(url)
    assert parsed.host in ("127.0.0.1", "localhost")
    assert parsed.database == "rpa_state_test"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("""
            DROP TABLE IF EXISTS tb_property, tb_address, tb_rpa_state, tb_log_rpa;
            CREATE TABLE tb_address (
                id SERIAL PRIMARY KEY, cep TEXT, city TEXT, state TEXT
            );
            CREATE TABLE tb_property (
                id SERIAL PRIMARY KEY, name TEXT,
                address_id INTEGER REFERENCES tb_address(id),
                UNIQUE (name, address_id)
            );
            CREATE TABLE tb_log_rpa (id SERIAL PRIMARY KEY, status TEXT);
        """))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(load, "create_second_year_connection", lambda: engine)
    yield engine
    engine.dispose()


def migration_data():
    return {
        "tb_address": pd.DataFrame([
            {"id": 1, "cep": "01001000", "city": "SAO PAULO", "state": "SP"},
            {"id": 2, "cep": "01001000", "city": "SAO PAULO", "state": "SP"},
        ]),
        "tb_property": pd.DataFrame([
            {"id": 10, "name": "UNIDADE", "address_id": 1},
            {"id": 20, "name": "UNIDADE", "address_id": 2},
        ]),
    }


def counts(engine):
    with engine.connect() as connection:
        return tuple(connection.execute(text(
            "SELECT (SELECT count(*) FROM tb_address), "
            "(SELECT count(*) FROM tb_property)"
        )).one())


@pytest.mark.parametrize("cache_state", ["missing", "stale", "corrupt"])
def test_replay_uses_database_state_instead_of_local_file(database, cache_state):
    first = load.load_data(migration_data())
    assert first["tb_address"]["inserted"] == 2
    assert counts(database) == (2, 2)

    path = state._id_map_path()
    if cache_state == "missing":
        os.remove(path)
    elif cache_state == "stale":
        state.save_id_map({"tb_address": {1: 999}})
    else:
        with open(path, "w", encoding="utf-8") as cache:
            cache.write("invalid JSON")

    second = load.load_data(migration_data())
    assert second["tb_address"] == {"inserted": 0, "updated": 2, "deleted": 0}
    assert second["tb_property"]["inserted"] == 0
    assert counts(database) == (2, 2)


def test_cache_write_failure_after_commit_is_recoverable(database, monkeypatch):
    monkeypatch.setattr(load, "save_id_map", lambda mapping: (_ for _ in ()).throw(OSError("disk full")))
    load.load_data(migration_data())
    assert not os.path.exists(state._id_map_path())
    assert counts(database) == (2, 2)
    load.load_data(migration_data())
    assert counts(database) == (2, 2)


def test_state_write_failure_rolls_back_addresses_and_properties(database, monkeypatch):
    monkeypatch.setattr(load, "save_database_id_map", lambda *args: (_ for _ in ()).throw(RuntimeError("state write failed")))
    with pytest.raises(RuntimeError, match="state write failed"):
        load.load_data(migration_data())
    assert counts(database) == (0, 0)
    assert not os.path.exists(state._id_map_path())


def test_existing_json_is_imported_without_reinserting_rows(database):
    with database.begin() as connection:
        connection.execute(text("INSERT INTO tb_address(id, cep) VALUES (41, '01001000'), (42, '01001000')"))
        connection.execute(text("INSERT INTO tb_property(id, name, address_id) VALUES (51, 'UNIDADE', 41), (52, 'UNIDADE', 42)"))
        connection.execute(text("INSERT INTO tb_log_rpa(status) VALUES ('SUCCESS')"))
    state.save_id_map({"tb_address": {1: 41, 2: 42}, "tb_property": {10: 51, 20: 52}})
    result = load.load_data(migration_data())
    assert result["tb_address"]["updated"] == 2
    assert result["tb_property"]["updated"] == 2
    assert counts(database) == (2, 2)


def test_first_activation_refuses_lost_state_from_earlier_runs(database):
    with database.begin() as connection:
        connection.execute(text("INSERT INTO tb_log_rpa(status) VALUES ('SUCCESS')"))
    with pytest.raises(RuntimeError, match="execuções anteriores"):
        load.load_data(migration_data())
    assert counts(database) == (0, 0)


def test_empty_existing_json_is_a_valid_bootstrap_state(database):
    with database.begin() as connection:
        connection.execute(text("INSERT INTO tb_log_rpa(status) VALUES ('SUCCESS')"))
    state.save_id_map({})
    load.load_data(migration_data())
    assert counts(database) == (2, 2)


def test_transaction_lock_serializes_loads(database):
    with database.connect() as first, database.connect() as second:
        first_transaction = first.begin()
        state.load_database_id_map(first)
        assert second.execute(text("SELECT pg_try_advisory_xact_lock(16481273)")).scalar_one() is False
        second.rollback()
        first_transaction.rollback()
        assert second.execute(text("SELECT pg_try_advisory_xact_lock(16481273)")).scalar_one() is True
