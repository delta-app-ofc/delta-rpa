import pandas as pd

from database.connections import create_first_year_connection

ALLOWED_TABLES = {
    "tb_user",
    "tb_last_water_bill",
    "tb_user_habit",
    "tb_user_habit_day",
    "tb_address",
    "tb_property",
    "tb_user_property",
    "tb_device"
}

# O banco do primeiro ano prefixa algumas colunas com o nome da tabela
# (ex.: tb_user.user_name) para evitar ambiguidade no CRUD administrativo deles.
# Aqui elas voltam para o nome genérico que o resto do RPA (validação,
# transformação e o banco novo) espera.
LEGACY_COLUMN_RENAMES = {
    "tb_user": {
        "user_name": "name",
        "user_password": "password"
    },
    "tb_last_water_bill": {
        "bill_month": "month"
    },
    "tb_address": {
        "adress_state": "state"
    },
    "tb_property": {
        "property_name": "name",
        "property_type": "type"
    }
}


def _rename_legacy_columns(
    table: str,
    dataframe: pd.DataFrame
) -> pd.DataFrame:

    renames = LEGACY_COLUMN_RENAMES.get(table, {})

    existing = {
        old_name: new_name
        for old_name, new_name in renames.items()
        if old_name in dataframe.columns
    }

    if not existing:
        return dataframe

    return dataframe.rename(columns=existing)


def find_table(table:str ) -> pd.DataFrame:

    if table  not in ALLOWED_TABLES:
        raise ValueError(
            f"Tabela '{table}' não permitida."
        )

    connection = create_first_year_connection()
    query = f"SELECT * FROM {table}"
    dataframe = pd.read_sql(query, connection)

    return _rename_legacy_columns(table, dataframe)

def find_tables(tables: list[str]) -> dict[str,pd.DataFrame]:
    data = {}

    for table in tables:
        data[table] = find_table(table)
    
    return data