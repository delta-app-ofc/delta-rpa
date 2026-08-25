import pandas as pd
from datetime import date


RULES = {

    "tb_user": {

        "min_age": {
            "birth_date": 18
        }

    },

    "tb_property": {

        "allowed_source_values": {
            "type": [
                "CASA",
                "APARTAMENTO"
            ]
        }

    },

    "tb_last_water_bill": {

        "first_day_of_month": [
            "month"
        ]

    }
}

UNIQUE_COLUMNS = {

    "tb_region": [
        ["name"]
    ],

    "tb_day_of_week": [
        ["name"]
    ],

    "tb_habit": [
        ["name"]
    ],

    "tb_user": [
        ["email"]
    ],

    "tb_user_property": [
        ["user_id", "property_id"]
    ],

    "tb_device": [
        ["device_id"]
    ],

    "tb_user_habit": [
        ["user_id", "habit_id"]
    ],

    "tb_user_habit_day": [
        ["user_habit_id", "day_of_week_id"]
    ],

    "tb_last_water_bill": [
        ["user_id", "month"]
    ]
}


FOREIGN_KEYS = {

    "tb_address": {
        "region_id": ("tb_region", "id")
    },

    "tb_property": {
        "address_id": ("tb_address", "id")
    },

    "tb_user_property": {
        "user_id": ("tb_user", "id"),
        "property_id": ("tb_property", "id")
    },

    "tb_device": {
        "property_id": ("tb_property", "id")
    },

    "tb_region_rate": {
        "region_id": ("tb_region", "id")
    },

    "tb_user_habit": {
        "user_id": ("tb_user", "id"),
        "habit_id": ("tb_habit", "id")
    },

    "tb_user_habit_day": {
        "user_habit_id": ("tb_user_habit", "id"),
        "day_of_week_id": ("tb_day_of_week", "id")
    },

    "tb_last_water_bill": {
        "user_id": ("tb_user", "id")
    }
}


VALIDATION_PRIORITY = [
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

def _add_error(
    errors: list,
    index,
    column: str,
    message: str
):
    """
    Adiciona um erro à lista de erros.

    Armazena o índice do registro, a coluna onde o erro
    ocorreu e a mensagem correspondente.
    """
    errors.append({
        "index": index,
        "column": column,
        "error": message
    })


def _validate_age(
    dataframe: pd.DataFrame,
    rules: dict,
    errors: list
):
    """
    Valida a idade dos registros com base na data de nascimento.

    Percorre as colunas configuradas nas regras, converte a data
    de nascimento e verifica se a idade do registro atende à
    idade mínima definida.
    """
    today = date.today()

    for column, minimum_age in rules.items():

        if column not in dataframe.columns:
            continue

        for index, value in dataframe[column].items():

            if pd.isna(value):
                continue

            birth_date = pd.to_datetime(
                value,
                errors="coerce"
            )

            if pd.isna(birth_date):

                _add_error(
                    errors,
                    index,
                    column,
                    "Data de nascimento inválida."
                )

                continue

            birth_date = birth_date.date()

            age = (
                today.year
                - birth_date.year
                - (
                    (today.month, today.day)
                    < (birth_date.month, birth_date.day)
                )
            )

            if age < minimum_age:

                _add_error(
                    errors,
                    index,
                    column,
                    f"Idade mínima: {minimum_age} anos."
                )


def _validate_source_values(
    dataframe: pd.DataFrame,
    rules: dict,
    errors: list
):
    """
    Valida se os valores das colunas estão entre os valores permitidos.

    Verifica os valores definidos nas regras de origem e registra
    os registros que possuem valores diferentes dos esperados.
    """
    for column, allowed_values in rules.items():

        if column not in dataframe.columns:
            continue

        records = dataframe[
            dataframe[column].notna()
            & ~dataframe[column].isin(allowed_values)
        ]

        for index in records.index:

            value = dataframe.at[index, column]

            _add_error(
                errors,
                index,
                column,
                f"Valor '{value}' não esperado no banco legado."
            )


def _validate_first_day_of_month(
    dataframe: pd.DataFrame,
    columns: list,
    errors: list
):
    """
    Valida se as datas informadas representam o primeiro dia do mês.

    Converte os valores das colunas para data e registra um erro
    quando o dia da data for diferente de 1.
    """
    for column in columns:

        if column not in dataframe.columns:
            continue

        for index, value in dataframe[column].items():

            if pd.isna(value):
                continue

            converted_date = pd.to_datetime(
                value,
                errors="coerce"
            )

            if pd.isna(converted_date):
                continue

            if converted_date.day != 1:

                _add_error(
                    errors,
                    index,
                    column,
                    "A data deve representar o primeiro dia do mês."
                )


def _validate_foreign_keys(
    dataframes: dict[str, pd.DataFrame],
    errors: list
):
    """
    Valida as chaves estrangeiras entre os DataFrames.

    Verifica se os valores das colunas que representam chaves
    estrangeiras existem na tabela e coluna referenciadas.
    """
    for table, relationships in FOREIGN_KEYS.items():

        if table not in dataframes:
            continue

        dataframe = dataframes[table]

        for column, (
            referenced_table,
            referenced_column
        ) in relationships.items():

            if column not in dataframe.columns:
                continue

            if referenced_table not in dataframes:
                continue

            referenced_dataframe = dataframes[
                referenced_table
            ]

            if referenced_column not in referenced_dataframe.columns:
                continue

            valid_values = set(
                referenced_dataframe[
                    referenced_column
                ].dropna()
            )

            invalid_records = dataframe[
                dataframe[column].notna()
                & ~dataframe[column].isin(valid_values)
            ]

            for index in invalid_records.index:

                value = dataframe.at[
                    index,
                    column
                ]

                _add_error(
                    errors,
                    index,
                    column,
                    (
                        f"Valor '{value}' não encontrado "
                        f"em {referenced_table}.{referenced_column}."
                    )
                )

def _validate_duplicates(
    dataframe: pd.DataFrame,
    rules: list,
    errors: list
):
    """
    Valida duplicidades de acordo com as restrições UNIQUE da tabela.
    """

    for columns in rules:

        existing_columns = [
            column
            for column in columns
            if column in dataframe.columns
        ]

        if len(existing_columns) != len(columns):
            continue

        duplicated = dataframe[
            dataframe.duplicated(
                subset=columns,
                keep=False
            )
        ]

        for index in duplicated.index:

            values = ", ".join(
                f"{column}='{dataframe.at[index, column]}'"
                for column in columns
            )

            _add_error(
                errors,
                index,
                ", ".join(columns),
                f"Registro duplicado: {values}."
            )


def _validate_table(
    table: str,
    dataframe: pd.DataFrame
):
    """
    Executa as validações configuradas para uma tabela.

    Obtém as regras da tabela e executa as validações de idade,
    valores permitidos e primeiro dia do mês.
    """
    errors = []

    rules = RULES.get(
        table,
        {}
    )

    _validate_age(
        dataframe,
        rules.get("min_age", {}),
        errors
    )

    _validate_source_values(
        dataframe,
        rules.get("allowed_source_values", {}),
        errors
    )

    _validate_first_day_of_month(
        dataframe,
        rules.get("first_day_of_month", []),
        errors
    )

    _validate_duplicates(
        dataframe,
        UNIQUE_COLUMNS.get(table, []),
        errors
    )

    return errors

def validate_data(
    dataframes: dict[str, pd.DataFrame]
):
    valid_data = {}
    errors_by_table = {}

    for table in VALIDATION_PRIORITY:

        if table not in dataframes:
            continue

        dataframe = dataframes[table]
        errors = _validate_table(table, dataframe)

        if errors:
            errors_by_table[table] = pd.DataFrame(errors)

            invalid_indexes = {
                error["index"]
                for error in errors
                if error["index"] is not None
            }

            valid_data[table] = dataframe[
                ~dataframe.index.isin(invalid_indexes)
            ].copy()

        else:
            valid_data[table] = dataframe.copy()

    foreign_key_errors = []

    _validate_foreign_keys(
        valid_data,
        foreign_key_errors
    )

    if foreign_key_errors:
        errors_by_table["foreign_keys"] = pd.DataFrame(
            foreign_key_errors
        )

    return {
        "valid": valid_data,
        "errors": errors_by_table
    }

