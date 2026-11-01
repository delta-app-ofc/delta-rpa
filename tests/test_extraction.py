import pandas as pd
import pytest

from modules import extraction


def test_rejects_unlisted_table_before_opening_database(monkeypatch):
    opened = []
    monkeypatch.setattr(
        extraction,
        "create_first_year_connection",
        lambda: opened.append(True),
    )

    with pytest.raises(ValueError, match="não permitida"):
        extraction.find_table("tb_user; DROP TABLE tb_user")

    assert opened == []


def test_reads_only_an_allowlisted_table(monkeypatch):
    connection = object()
    expected = pd.DataFrame({"id": [1]})
    statements = []
    monkeypatch.setattr(
        extraction, "create_first_year_connection", lambda: connection
    )
    monkeypatch.setattr(
        extraction.pd,
        "read_sql",
        lambda query, conn: statements.append((query, conn)) or expected,
    )

    result = extraction.find_table("tb_user")

    assert result is expected
    assert statements == [("SELECT * FROM tb_user", connection)]


def test_find_tables_preserves_requested_order_and_results(monkeypatch):
    calls = []
    monkeypatch.setattr(
        extraction,
        "find_table",
        lambda name: calls.append(name) or pd.DataFrame({"table": [name]}),
    )

    result = extraction.find_tables(["tb_address", "tb_device"])

    assert calls == ["tb_address", "tb_device"]
    assert list(result) == ["tb_address", "tb_device"]
    assert result["tb_device"].iloc[0]["table"] == "tb_device"


def test_renames_legacy_columns_to_canonical_names():
    dataframe = pd.DataFrame([
        {"id": 1, "user_name": "Ana", "user_password": "senha123", "email": "ana@x.com"},
    ])

    result = extraction._rename_legacy_columns("tb_user", dataframe)

    assert list(result.columns) == ["id", "name", "password", "email"]


def test_keeps_columns_unchanged_for_table_without_renames():
    dataframe = pd.DataFrame({"id": [1]})

    result = extraction._rename_legacy_columns("tb_user_property", dataframe)

    assert result is dataframe


def test_ignores_renames_for_columns_not_present():
    dataframe = pd.DataFrame({"id": [1]})

    result = extraction._rename_legacy_columns("tb_user", dataframe)

    assert result is dataframe
