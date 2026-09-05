"""
Registro de cada execução do RPA na tabela ``tb_log_rpa`` do banco novo.

A cada execução é gravada uma linha com o horário de início (``start_execution_log``)
e, ao final, a mesma linha é atualizada com o horário de término, o status
(``SUCCESS`` ou ``ERROR``), a quantidade de registros inseridos, atualizados e
excluídos, a quantidade de erros de validação e a mensagem de erro, quando houver
(``finish_execution_log``).

Este log é gravado em uma transação própria, separada da transação da carga. Se a
carga falhar e sofrer rollback, a linha de log continua registrada com o status
``ERROR``.
"""

from sqlalchemy import text

from database.connections import create_second_year_connection


def start_execution_log() -> int:
    """
    Insere a linha inicial da execução em ``tb_log_rpa`` e devolve o id gerado.

    A linha nasce com ``status = 'RUNNING'`` e contadores zerados (valores padrão
    definidos na própria tabela).
    """
    engine = create_second_year_connection()

    query = text(
        """
        INSERT INTO tb_log_rpa (status)
        VALUES ('RUNNING')
        RETURNING id
        """
    )

    with engine.begin() as connection:
        result = connection.execute(query)
        return result.scalar_one()


def finish_execution_log(
    log_id: int,
    status: str,
    inserted_count: int,
    updated_count: int,
    deleted_count: int,
    validation_error_count: int,
    error_message: str = None
) -> None:
    """
    Atualiza a linha da execução em ``tb_log_rpa`` com o resultado final.

    Se ``log_id`` for ``None`` (a linha inicial não pôde ser criada), a função não
    faz nada.
    """
    if log_id is None:
        return

    engine = create_second_year_connection()

    query = text(
        """
        UPDATE tb_log_rpa
        SET finished_at = CURRENT_TIMESTAMP,
            status = :status,
            inserted_count = :inserted_count,
            updated_count = :updated_count,
            deleted_count = :deleted_count,
            validation_error_count = :validation_error_count,
            error_message = :error_message
        WHERE id = :log_id
        """
    )

    values = {
        "status": status,
        "inserted_count": inserted_count,
        "updated_count": updated_count,
        "deleted_count": deleted_count,
        "validation_error_count": validation_error_count,
        "error_message": error_message,
        "log_id": log_id,
    }

    with engine.begin() as connection:
        connection.execute(query, values)
