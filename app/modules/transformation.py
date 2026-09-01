import pandas as pd

TRANSFORMATIONS = {

    "tb_address": {
        "uppercase": [
            "city",
            "state"
        ]
    },

    "tb_user": {
        "uppercase": [
            "name",
            "email"
        ]
    },

    "tb_property": {
        "uppercase": [
            "name",
            "type",
            "classification"
        ],

        "replace": {
            "type": {
                "APARTAMENTO": "PRÉDIO"
            }
        }
    },

    "tb_device": {
        "uppercase": [
            "device_id"
        ]
    }
}


def _transform_uppercase(
    dataframe: pd.DataFrame,
    columns: list[str]
):
    dataframe = dataframe.copy()

    for column in columns:

        if column not in dataframe.columns:
            continue

        for index, value in dataframe[column].items():

            if isinstance(value, str):
                dataframe.at[index, column] = value.upper()

    return dataframe

def _transform_replace(
    dataframe: pd.DataFrame,
    rules: dict
):
    dataframe = dataframe.copy()

    for column, replacements in rules.items():

        if column not in dataframe.columns:
            continue

        dataframe[column] = dataframe[column].replace(
            replacements
        )

    return dataframe


def _transform_table(
    table: str,
    dataframe: pd.DataFrame
):
    rules = TRANSFORMATIONS.get(
        table,
        {}
    )

    transformed = dataframe.copy()

    transformed = _transform_uppercase(
        transformed,
        rules.get("uppercase", [])
    )

    transformed = _transform_replace(
        transformed,
        rules.get("replace", {})
    )

    return transformed


def transform_data(
    dataframes: dict[str, pd.DataFrame]
):
    """
    Recebe os DataFrames validados e retorna
    os DataFrames preparados para a carga.
    """

    transformed_data = {}

    for table, dataframe in dataframes.items():

        transformed_data[table] = _transform_table(
            table,
            dataframe
        )

    return transformed_data