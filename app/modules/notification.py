"""
Envio do e-mail de resumo ao final de toda execução do RPA.

O e-mail é enviado sempre, tanto em caso de sucesso quanto de erro. Usa apenas a
biblioteca padrão do Python (``smtplib`` e ``email``), sem dependência nova.

As configurações vêm de variáveis de ambiente:

    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO

Se as variáveis obrigatórias (``SMTP_HOST``, ``EMAIL_FROM`` e ``EMAIL_TO``) não
estiverem preenchidas, o envio é apenas registrado no log e ignorado. Assim o RPA
continua funcionando em ambientes sem servidor de e-mail (por exemplo, nos
testes).
"""

import os
import smtplib
from email.message import EmailMessage

from modules.logs import get_logger


def _read_config() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": os.getenv("SMTP_PORT", ""),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "email_from": os.getenv("EMAIL_FROM", ""),
        "email_to": os.getenv("EMAIL_TO", ""),
    }


def build_report(summary: dict) -> tuple[str, str]:
    """
    Monta o assunto e o corpo (texto puro) do e-mail a partir do resumo da
    execução.

    O ``summary`` tem o formato:

        {
            "started_at": "2026-09-05 08:00:00",
            "finished_at": "2026-09-05 08:00:12",
            "status": "SUCCESS",
            "error_message": None,
            "tables": {
                "tb_user": {
                    "inserted": 2, "updated": 1,
                    "deleted": 0, "validation_errors": 0
                },
                ...
            }
        }
    """
    status = summary.get("status", "ERROR")

    subject = f"[RPA Delta] Execução {status}"

    lines = [
        f"Status geral: {status}",
        f"Início: {summary.get('started_at', '-')}",
        f"Fim: {summary.get('finished_at', '-')}",
        "",
        "Resumo por tabela:",
    ]

    tables = summary.get("tables", {})

    if tables:
        for table, counts in tables.items():
            lines.append(
                f"- {table}: "
                f"inseridos={counts.get('inserted', 0)}, "
                f"atualizados={counts.get('updated', 0)}, "
                f"excluídos={counts.get('deleted', 0)}, "
                f"erros de validação={counts.get('validation_errors', 0)}"
            )
    else:
        lines.append("- (nenhuma tabela processada)")

    error_message = summary.get("error_message")

    if error_message:
        lines.append("")
        lines.append(f"Erro: {error_message}")

    return subject, "\n".join(lines)


def send_execution_report(summary: dict) -> bool:
    """
    Envia o e-mail de resumo. Devolve ``True`` se o e-mail foi enviado e ``False``
    se foi ignorado (sem configuração) ou se o envio falhou.

    Uma falha no envio do e-mail nunca interrompe o RPA: ela é apenas registrada
    no log.
    """
    logger = get_logger()
    config = _read_config()

    if not config["host"] or not config["email_from"] or not config["email_to"]:
        logger.warning(
            "SMTP não configurado. E-mail de resumo não enviado."
        )
        return False

    subject, body = build_report(summary)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["email_from"]
    message["To"] = config["email_to"]
    message.set_content(body)

    port = int(config["port"]) if config["port"] else 587

    try:
        with smtplib.SMTP(config["host"], port) as server:
            server.starttls()

            if config["user"]:
                server.login(config["user"], config["password"])

            server.send_message(message)

        logger.info("E-mail de resumo enviado.")
        return True

    except Exception as exception:
        logger.error(
            f"Falha ao enviar e-mail de resumo | erro={exception}"
        )
        return False
