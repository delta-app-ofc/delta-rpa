import logging

import pandas as pd
import pytest

from modules import load
from modules.load import _apply_deletions, _apply_upserts, _insert_row


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class FakeConnection:
    """
    Conexão falsa que apenas registra os comandos SQL executados.

    Assim os testes verificam a decisão do RPA (inserir, atualizar ou excluir)
    sem precisar de um banco de dados real.
    """

    def __init__(self, start_id: int = 1000):
        self.statements = []
        self._next_id = start_id

    def execute(self, statement, parameters=None):
        sql = str(statement)
        self.statements.append((sql, parameters or {}))

        if "RETURNING id" in sql:
            self._next_id += 1
            return _FakeResult(self._next_id)

        return _FakeResult(None)


@pytest.fixture(autouse=True)
def _silent_logger(monkeypatch):
    # Evita criar arquivo de log durante os testes.
    monkeypatch.setattr(load, "get_logger", lambda: logging.getLogger("rpa-test"))


def _sql_list(connection):
    return [sql for sql, _ in connection.statements]


# --------------------------------------------------------------------------- #
# Inserção x atualização (R2)
# --------------------------------------------------------------------------- #

def test_new_row_is_inserted_and_recorded_in_id_map():
    connection = FakeConnection()
    id_map = {}
    counts = {}

    dataframes = {
        "tb_address": pd.DataFrame([
            {"id": 1, "region_id": 3, "cep": "01001000", "city": "SP", "state": "SP"}
        ])
    }

    _apply_upserts(connection, dataframes, id_map, counts)

    joined = " ".join(_sql_list(connection))

    assert "INSERT INTO tb_address" in joined
    assert "UPDATE tb_address" not in joined
    assert counts["tb_address"]["inserted"] == 1
    assert id_map["tb_address"][1] == 1001


def test_known_row_is_updated_with_all_columns():
    connection = FakeConnection()
    id_map = {"tb_address": {1: 555}}
    counts = {}

    dataframes = {
        "tb_address": pd.DataFrame([
            {"id": 1, "region_id": 3, "cep": "02002000", "city": "RJ", "state": "RJ"}
        ])
    }

    _apply_upserts(connection, dataframes, id_map, counts)

    statement, parameters = connection.statements[0]

    assert "UPDATE tb_address" in statement
    for column in ("region_id", "cep", "city", "state"):
        assert f"{column} = :{column}" in statement
    assert "WHERE id = :target_id" in statement
    assert parameters["target_id"] == 555
    assert counts["tb_address"]["updated"] == 1
    assert "INSERT" not in " ".join(_sql_list(connection))


def test_unique_table_insert_uses_on_conflict():
    connection = FakeConnection()

    dataframes = {
        "tb_region_rate": pd.DataFrame([
            {
                "id": 1,
                "region_id": 2,
                "m3_value": 5.5,
                "initial_validity": "2026-01-01",
                "final_validity": None,
            }
        ])
    }

    _apply_upserts(connection, dataframes, {}, {})

    statement = connection.statements[0][0]

    assert "INSERT INTO tb_region_rate" in statement
    assert "ON CONFLICT (region_id, initial_validity)" in statement
    assert "DO UPDATE SET" in statement


def test_property_insert_uses_on_conflict_name_address():
    connection = FakeConnection()

    dataframes = {
        "tb_property": pd.DataFrame([
            {
                "id": 1,
                "name": "X",
                "type": "CASA",
                "classification": "RESIDENCIAL",
                "address_id": 9,
            }
        ])
    }

    _apply_upserts(connection, dataframes, {}, {})

    statement = connection.statements[0][0]

    assert "INSERT INTO tb_property" in statement
    assert "ON CONFLICT (name, address_id)" in statement
    assert "DO UPDATE SET" in statement


def test_insert_row_without_natural_key_is_plain_insert():
    connection = FakeConnection()

    # Tabela fora de UNIQUE_COLUMNS: sem ON CONFLICT.
    _insert_row(connection, "tb_sem_chave", ["a", "b"], {"a": 1, "b": 2})

    statement = connection.statements[0][0]

    assert "INSERT INTO tb_sem_chave" in statement
    assert "ON CONFLICT" not in statement


# --------------------------------------------------------------------------- #
# Detecção e replicação de exclusão (R3)
# --------------------------------------------------------------------------- #

def test_deleted_legacy_row_is_removed_and_dropped_from_id_map():
    connection = FakeConnection()
    id_map = {"tb_device": {1: 11, 2: 22}}
    counts = {}

    # O id 2 sumiu da extração desta execução: foi apagado no legado.
    _apply_deletions(connection, {"tb_device": {1}}, id_map, counts)

    statement, parameters = connection.statements[0]

    assert "DELETE FROM tb_device" in statement
    assert parameters["target_id"] == 22
    assert id_map["tb_device"] == {1: 11}
    assert counts["tb_device"]["deleted"] == 1


def test_deletions_follow_reverse_load_priority():
    connection = FakeConnection()

    id_map = {
        "tb_user": {1: 1, 2: 2},
        "tb_last_water_bill": {8: 80, 9: 90},
    }
    extracted_ids = {
        "tb_user": {1},
        "tb_last_water_bill": {8},
    }

    _apply_deletions(connection, extracted_ids, id_map, {})

    deleted_tables = [
        sql.split("DELETE FROM ")[1].split(" ")[0]
        for sql in _sql_list(connection)
    ]

    assert deleted_tables.index("tb_last_water_bill") < deleted_tables.index("tb_user")


def test_table_absent_from_extraction_is_not_touched():
    connection = FakeConnection()
    id_map = {"tb_device": {1: 11, 2: 22}}

    _apply_deletions(connection, {"tb_user": {1}}, id_map, {})

    assert connection.statements == []
    assert id_map["tb_device"] == {1: 11, 2: 22}


def test_no_deletion_when_every_id_is_still_present():
    connection = FakeConnection()
    id_map = {"tb_device": {1: 11}}

    _apply_deletions(connection, {"tb_device": {1}}, id_map, {})

    assert connection.statements == []
