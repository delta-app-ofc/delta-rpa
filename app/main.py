from datetime import datetime

from modules.extraction import find_tables
from modules.validation import validate_data
from modules.transformation import transform_data
from modules.load import load_data
from modules.execution_log import start_execution_log, finish_execution_log
from modules.logs import (
    get_logger,
    log_start,
    log_end,
    log_extraction,
    log_validation,
    log_transformation,
    log_error
)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _build_extracted_ids(data: dict) -> dict:
    """
    Monta {tabela: conjunto de ids do legado} a partir dos dados extraídos.

    É usado pela carga para detectar quais registros foram apagados no banco
    legado desde a última execução.
    """
    extracted_ids = {}

    for table, dataframe in data.items():

        if "id" not in dataframe.columns:
            continue

        extracted_ids[table] = {
            int(value)
            for value in dataframe["id"].dropna().tolist()
        }

    return extracted_ids


def _table_summary(summary: dict, table: str) -> dict:
    """
    Devolve (criando se necessário) o resumo de uma tabela, com contadores
    zerados.
    """
    return summary["tables"].setdefault(
        table,
        {
            "inserted": 0,
            "updated": 0,
            "deleted": 0,
            "validation_errors": 0
        }
    )


def _merge_validation_errors(summary: dict, errors: dict) -> None:
    for table, dataframe in errors.items():
        _table_summary(summary, table)["validation_errors"] = len(dataframe)


def _merge_load_counts(summary: dict, load_counts: dict) -> None:
    for table, counts in load_counts.items():
        table_summary = _table_summary(summary, table)
        table_summary["inserted"] = counts.get("inserted", 0)
        table_summary["updated"] = counts.get("updated", 0)
        table_summary["deleted"] = counts.get("deleted", 0)


def _totals(summary: dict) -> dict:
    tables = summary["tables"].values()

    return {
        "inserted": sum(table["inserted"] for table in tables),
        "updated": sum(table["updated"] for table in tables),
        "deleted": sum(table["deleted"] for table in tables),
        "validation_errors": sum(
            table["validation_errors"] for table in tables
        ),
    }


def main():

    logger = get_logger()

    log_start(logger)

    TABLES = {
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

    summary = {
        "started_at": _now(),
        "finished_at": None,
        "status": "ERROR",
        "error_message": None,
        "tables": {}
    }

    log_id = None

    try:

        log_id = start_execution_log()

        # 1. EXTRAÇÃO
        data = find_tables(TABLES)

        for table, dataframe in data.items():
            log_extraction(logger, table, len(dataframe))

        extracted_ids = _build_extracted_ids(data)

        # 2. VALIDAÇÃO
        validation_result = validate_data(data)

        valid_data = validation_result["valid"]
        errors = validation_result["errors"]

        for table, dataframe in valid_data.items():

            table_errors = errors.get(table)

            error_quantity = (
                len(table_errors)
                if table_errors is not None
                else 0
            )

            log_validation(
                logger,
                table,
                len(dataframe),
                error_quantity
            )

        _merge_validation_errors(summary, errors)

        # 3. TRANSFORMAÇÃO
        transformed_data = transform_data(valid_data)

        for table, dataframe in transformed_data.items():
            log_transformation(logger, table, len(dataframe))

        # 4. CARGA
        load_counts = load_data(transformed_data, extracted_ids)

        _merge_load_counts(summary, load_counts)

        # 5. FINALIZAÇÃO
        summary["status"] = "SUCCESS"

        log_end(logger)

    except Exception as exception:

        summary["status"] = "ERROR"
        summary["error_message"] = str(exception)

        log_error(
            logger,
            "Erro durante a execução do RPA",
            exception
        )

        raise

    finally:

        summary["finished_at"] = _now()

        totals = _totals(summary)

        try:
            finish_execution_log(
                log_id,
                summary["status"],
                totals["inserted"],
                totals["updated"],
                totals["deleted"],
                totals["validation_errors"],
                summary["error_message"]
            )
        except Exception as exception:
            log_error(
                logger,
                "Falha ao gravar o fim da execução em tb_log_rpa",
                exception
            )


if __name__ == "__main__":
    main()
