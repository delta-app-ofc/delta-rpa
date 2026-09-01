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
    "tb_region_rate",
    "tb_device"
}

def find_table(table:str ) -> pd.DataFrame:

    if table  not in ALLOWED_TABLES:
        raise ValueError(
            f"Tabela '{table}' não permitida."
        )

    connection = create_first_year_connection()
    query = f"SELECT * FROM {table}"
    return pd.read_sql(query, connection)

def find_tables(tables: list[str]) -> dict[str,pd.DataFrame]:
    data = {}

    for table in tables:
        data[table] = find_table(table)
    
    return data