import pandas as pd
from sqlalchemy import text
from database.connections import create_second_year_connection
from modules.validation import FOREIGN_KEYS
from modules.state import load_id_map, save_id_map
from modules.logs import (
    get_logger,
    log_load,
    log_commit,
    log_rollback,
    log_delete
)

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

# Chaves naturais (colunas únicas) usadas no INSERT ... ON CONFLICT.
#
# Cada tabela aqui precisa ter, no banco novo, uma restrição UNIQUE
# correspondente nessas mesmas colunas. Quando o mapa de ids ainda não conhece
# um registro, o ON CONFLICT reconcilia pela chave natural em vez de duplicar.
UNIQUE_COLUMNS = {
    "tb_user": ["email"],
    "tb_region": ["name"],
    "tb_day_of_week": ["name"],
    "tb_habit": ["name"],
    "tb_address": ["cep"],
    "tb_property": ["name", "address_id"],
    "tb_device": ["device_id"],
    "tb_user_property": ["user_id", "property_id"],
    "tb_region_rate": ["region_id", "initial_validity"],
    "tb_user_habit": ["user_id", "habit_id"],
    "tb_user_habit_day": ["user_habit_id", "day_of_week_id"],
    "tb_last_water_bill": ["user_id", "month"]
}


def _empty_counts() -> dict:
    return {"inserted": 0, "updated": 0, "deleted": 0}


def _row_values(row: pd.Series, columns: list) -> dict:
    """
    Converte uma linha do DataFrame em um dicionário de parâmetros para o SQL,
    tratando valores nulos e tipos do numpy/pandas.
    """
    values = {}

    for column in columns:

        value = row[column]

        if pd.isna(value):
            value = None

        elif hasattr(value, "item"):
            value = value.item()

        values[column] = value

    return values


def _replace_foreign_keys(
    table: str,
    dataframe: pd.DataFrame,
    id_map: dict
):
    """
    Substitui, nas colunas de chave estrangeira, os ids do banco legado pelos ids
    correspondentes no banco novo, usando o mapa de ids.

    Tabelas que não são migradas pelo RPA (tb_region, tb_habit, tb_day_of_week)
    não aparecem no mapa de ids; nesse caso a coluna é mantida como está, porque
    esses registros têm o mesmo id nos dois bancos.
    """
    dataframe = dataframe.copy()

    relationships = FOREIGN_KEYS.get(table, {})

    for column, (
        referenced_table,
        _referenced_column
    ) in relationships.items():

        if column not in dataframe.columns:
            continue

        if referenced_table not in id_map:
            continue

        dataframe[column] = dataframe[column].map(
            id_map[referenced_table]
        )

    return dataframe


def _insert_row(
    connection,
    table: str,
    columns: list,
    values: dict
) -> int:
    """
    Insere uma linha nova e devolve o id gerado no banco novo.

    Para tabelas com chave natural, usa ON CONFLICT como rede de segurança: se a
    linha já existir (por exemplo, migrada antes de o mapa de ids passar a ser
    persistido), ela é atualizada em vez de duplicada.
    """
    columns_names = ", ".join(columns)
    parameter_names = ", ".join(f":{column}" for column in columns)

    unique_columns = UNIQUE_COLUMNS.get(table)

    if unique_columns:
        conflict_columns = ", ".join(unique_columns)

        update_columns = ", ".join(
            f"{column} = EXCLUDED.{column}"
            for column in columns
        )

        query = text(
            f"""
            INSERT INTO {table} ({columns_names})
            VALUES ({parameter_names})
            ON CONFLICT ({conflict_columns})
            DO UPDATE SET {update_columns}
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

    result = connection.execute(query, values)

    return result.scalar_one()


def _update_row(
    connection,
    table: str,
    columns: list,
    values: dict,
    new_id: int
) -> None:
    """
    Atualiza todas as colunas de uma linha já migrada, identificada pelo id do
    banco novo.
    """
    assignments = ", ".join(
        f"{column} = :{column}"
        for column in columns
    )

    query = text(
        f"""
        UPDATE {table}
        SET {assignments}
        WHERE id = :target_id
        """
    )

    parameters = dict(values)
    parameters["target_id"] = new_id

    connection.execute(query, parameters)


def _apply_deletions(
    connection,
    extracted_ids: dict,
    id_map: dict,
    counts: dict
) -> None:
    """
    Replica no banco novo as exclusões que já aconteceram no banco legado.

    Para cada tabela, compara os ids do legado presentes no mapa de ids (de
    execuções anteriores) com os ids do legado que vieram na extração desta
    execução. Todo id que estava no mapa e não veio mais foi apagado no legado e
    precisa ser apagado no banco novo.

    As exclusões seguem a ordem inversa de LOAD_PRIORITY para respeitar as
    dependências de chave estrangeira (filhos antes dos pais).
    """
    if not extracted_ids:
        return

    logger = get_logger()

    for table in reversed(LOAD_PRIORITY):

        # Se a tabela não foi extraída nesta execução, não dá para saber quais
        # registros foram apagados: não mexe em nada.
        if table not in extracted_ids:
            continue

        table_map = id_map.get(table, {})

        known_legacy_ids = set(table_map.keys())
        present_legacy_ids = extracted_ids[table]

        removed_legacy_ids = known_legacy_ids - present_legacy_ids

        if not removed_legacy_ids:
            continue

        query = text(f"DELETE FROM {table} WHERE id = :target_id")

        for legacy_id in sorted(removed_legacy_ids):

            new_id = table_map[legacy_id]

            connection.execute(query, {"target_id": new_id})

            del table_map[legacy_id]

            counts.setdefault(table, _empty_counts())
            counts[table]["deleted"] += 1

        log_delete(logger, table, counts[table]["deleted"])


def _apply_upserts(
    connection,
    dataframes: dict,
    id_map: dict,
    counts: dict
) -> None:
    """
    Insere os registros novos e atualiza os que já foram migrados.

    A decisão é feita pelo mapa de ids: se o id do legado já está no mapa, o
    registro é atualizado usando o id do banco novo; se não está, é inserido e o
    novo id é guardado no mapa.
    """
    logger = get_logger()

    for table in LOAD_PRIORITY:

        if table not in dataframes:
            continue

        dataframe = _replace_foreign_keys(
            table,
            dataframes[table],
            id_map
        )

        if dataframe.empty:
            log_load(logger, table, 0)
            continue

        columns = [
            column
            for column in dataframe.columns
            if column != "id"
        ]

        has_id_column = "id" in dataframe.columns

        table_map = id_map.setdefault(table, {})
        counts.setdefault(table, _empty_counts())

        for _, row in dataframe.iterrows():

            values = _row_values(row, columns)

            legacy_id = None

            if has_id_column:
                legacy_id = row["id"]

                if hasattr(legacy_id, "item"):
                    legacy_id = legacy_id.item()

            if legacy_id is not None and legacy_id in table_map:

                _update_row(
                    connection,
                    table,
                    columns,
                    values,
                    table_map[legacy_id]
                )

                counts[table]["updated"] += 1

            else:

                new_id = _insert_row(
                    connection,
                    table,
                    columns,
                    values
                )

                if legacy_id is not None:
                    table_map[legacy_id] = new_id

                counts[table]["inserted"] += 1

        log_load(logger, table, len(dataframe))


def load_data(
    dataframes: dict[str, pd.DataFrame],
    extracted_ids: dict[str, set] | None = None,
):
    """
    Carrega os dados no banco novo.

    Parâmetros:
        dataframes: dicionário {tabela: DataFrame} já validado e transformado.
        extracted_ids: dicionário {tabela: conjunto de ids do legado} vindo da
            extração desta execução, usado para detectar exclusões. Se não for
            informado, a detecção de exclusão é ignorada.

    Devolve um dicionário de contadores por tabela:
        {tabela: {"inserted": n, "updated": n, "deleted": n}}

    Toda a carga (exclusões + inserções + atualizações) acontece em uma única
    transação. Em caso de falha, é feito rollback e o mapa de ids não é
    regravado.
    """
    logger = get_logger()

    id_map = load_id_map()
    counts: dict[str, dict] = {}

    engine = create_second_year_connection()

    try:

        with engine.connect() as connection:

            with connection.begin():

                _apply_deletions(
                    connection,
                    extracted_ids or {},
                    id_map,
                    counts
                )

                _apply_upserts(
                    connection,
                    dataframes,
                    id_map,
                    counts
                )

        log_commit(logger)

        save_id_map(id_map)

        return counts

    except Exception:
        log_rollback(logger)
        raise
