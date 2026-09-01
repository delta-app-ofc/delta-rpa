import pandas as pd
from sqlalchemy import text
from database.connections import create_second_year_connection
from modules.validation import FOREIGN_KEYS
from modules.logs import get_logger, log_load, log_commit, log_rollback

LOAD_PRIORITY = [
    "tb_user",
    "tb_address",
    "tb_property",
    "tb_user_property",
    "tb_device",
    "tb_region_rate",
    "tb_user_habit",
    "tb_user_habit_day",
    "tb_last_water_bill"
]

UNIQUE_COLUMNS = {
    "tb_user": ["email"],
    "tb_region": ["name"],
    "tb_day_of_week": ["name"],
    "tb_habit": ["name"],
    "tb_device": ["device_id"],
    "tb_user_property": ["user_id", "property_id"],
    "tb_user_habit": ["user_id", "habit_id"],
    "tb_user_habit_day": ["user_habit_id", "day_of_week_id"],
    "tb_last_water_bill": ["user_id", "month"]
}

def _insert_table(
    connection,
    table: str,
    dataframe: pd.DataFrame
):
    if dataframe.empty:
        return {}

    columns = [
        column
        for column in dataframe.columns
        if column != "id"
    ]

    columns_names = ", ".join(columns)

    parameter_names = ", ".join(
        f":{column}"
        for column in columns
    )

    unique_columns = UNIQUE_COLUMNS.get(table)

    if unique_columns:
        conflict_columns = ", ".join(unique_columns)

        query = text(
            f"""
            INSERT INTO {table} ({columns_names})
            VALUES ({parameter_names})
            ON CONFLICT ({conflict_columns})
            DO UPDATE SET
                {unique_columns[0]} = EXCLUDED.{unique_columns[0]}
            RETURNING id
            """
        )

    else:
        query = text(
            f"""
            INSERT INTO {table} ({columns_names})
            VALUES ({parameter_names})
            RETURNING id
            """
        )

    id_map = {}

    for _, row in dataframe.iterrows():

        values = {}

        for column in columns:

            value = row[column]

            if pd.isna(value):
                value = None

            elif hasattr(value, "item"):
                value = value.item()

            values[column] = value

        result = connection.execute(
            query,
            values
        )

        new_id = result.scalar_one()

        if "id" in dataframe.columns:

            old_id = row["id"]

            if hasattr(old_id, "item"):
                old_id = old_id.item()

            id_map[old_id] = new_id

    return id_map

def _replace_foreign_keys(
    table: str,
    dataframe: pd.DataFrame,
    id_maps: dict
):
    dataframe = dataframe.copy()

    relationships = FOREIGN_KEYS.get(
        table,
        {}
    )

    for column, (
        referenced_table,
        referenced_column
    ) in relationships.items():

        if column not in dataframe.columns:
            continue

        if referenced_table not in id_maps:
            continue

        id_map = id_maps[referenced_table]

        dataframe[column] = dataframe[column].map(
            id_map
        )

    return dataframe

def load_data(
    dataframes: dict[str, pd.DataFrame],
):
    logger = get_logger()
    id_maps = {}

    engine = create_second_year_connection()

    try:

        with engine.connect() as connection:

            with connection.begin():

                for table in LOAD_PRIORITY:

                    if table not in dataframes:
                        continue

                    dataframe = dataframes[table]

                    dataframe = _replace_foreign_keys(
                        table,
                        dataframe,
                        id_maps
                    )

                    id_maps[table] = _insert_table(
                        connection,
                        table,
                        dataframe
                    )

                    log_load(
                        logger,
                        table,
                        len(dataframe)
                    )

        log_commit(logger)

        return id_maps

    except Exception:
        log_rollback(logger)
        raise