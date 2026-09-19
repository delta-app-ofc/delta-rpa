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
            },

            "classification": {
                "RESIDENCIAL": 1,  # RESIDENCIAL_NORMAL
                "COMERCIAL": 5     # COMERCIAL_NORMAL_INDUSTRIAL
            }
        },

        "rename": {
            "classification": "classification_id"
        }
    },

    "tb_device": {
        "to_string": [
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

def _transform_to_string(
    dataframe: pd.DataFrame,
    columns: list[str]
):
    """
    Converte colunas numéricas para texto.

    Necessário para ``tb_device.device_id``: no banco legado a coluna é inteira,
    mas no banco novo ela é ``VARCHAR(100)``. O ``int`` intermediário evita que um
    valor como ``123`` vire ``"123.0"``.
    """
    dataframe = dataframe.copy()

    def _to_string(value):
        if pd.isna(value):
            return value

        if isinstance(value, float) and value.is_integer():
            value = int(value)

        return str(value)

    for column in columns:

        if column not in dataframe.columns:
            continue

        # Substitui a coluna inteira para não misturar tipos (int e texto) na
        # mesma coluna.
        dataframe[column] = dataframe[column].map(_to_string).astype("object")

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


def _transform_rename(
    dataframe: pd.DataFrame,
    columns: dict
):
    dataframe = dataframe.copy()

    existing = {
        old_name: new_name
        for old_name, new_name in columns.items()
        if old_name in dataframe.columns
    }

    return dataframe.rename(columns=existing)


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

    transformed = _transform_to_string(
        transformed,
        rules.get("to_string", [])
    )

    transformed = _transform_replace(
        transformed,
        rules.get("replace", {})
    )

    transformed = _transform_rename(
        transformed,
        rules.get("rename", {})
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
