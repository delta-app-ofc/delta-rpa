import logging
import os
from datetime import datetime


LOG_DIRECTORY = "logs"


def _create_log_directory():
    os.makedirs(
        LOG_DIRECTORY,
        exist_ok=True
    )


def _get_log_filename():
    date = datetime.now().strftime("%Y-%m-%d")

    return os.path.join(
        LOG_DIRECTORY,
        f"rpa_{date}.log"
    )


def get_logger():
    _create_log_directory()

    logger = logging.getLogger("rpa")

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(
        _get_log_filename(),
        encoding="utf-8"
    )

    file_handler.setFormatter(
        formatter
    )

    console_handler = logging.StreamHandler()

    console_handler.setFormatter(
        formatter
    )

    logger.addHandler(
        file_handler
    )

    logger.addHandler(
        console_handler
    )

    return logger


def log_start(logger):
    logger.info(
        "========== INÍCIO DA EXECUÇÃO DO RPA =========="
    )


def log_end(logger):
    logger.info(
        "=========== FIM DA EXECUÇÃO DO RPA ==========="
    )


def log_extraction(
    logger,
    table: str,
    quantity: int
):
    logger.info(
        f"Extração | tabela={table} | registros={quantity}"
    )


def log_validation(
    logger,
    table: str,
    valid: int,
    errors: int
):
    logger.info(
        (
            f"Validação | tabela={table} | "
            f"válidos={valid} | erros={errors}"
        )
    )


def log_transformation(
    logger,
    table: str,
    quantity: int
):
    logger.info(
        (
            f"Transformação | tabela={table} | "
            f"registros={quantity}"
        )
    )


def log_load(
    logger,
    table: str,
    quantity: int
):
    logger.info(
        (
            f"Carga | tabela={table} | "
            f"registros={quantity}"
        )
    )


def log_delete(
    logger,
    table: str,
    quantity: int
):
    logger.info(
        (
            f"Exclusão | tabela={table} | "
            f"registros={quantity}"
        )
    )


def log_commit(logger):
    logger.info(
        "Transação confirmada com COMMIT."
    )


def log_rollback(logger):
    logger.error(
        "Falha na carga. ROLLBACK realizado."
    )


def log_error(
    logger,
    message: str,
    exception: Exception
):
    logger.error(
        f"{message} | erro={exception}",
        exc_info=True
    )