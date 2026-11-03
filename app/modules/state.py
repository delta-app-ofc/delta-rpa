import json
import os
from sqlalchemy import text


STATE_DIRECTORY = "state"
ID_MAP_FILENAME = "id_map.json"


def _id_map_path():
    return os.path.join(STATE_DIRECTORY, ID_MAP_FILENAME)


def load_id_map() -> dict:
    """
    Lê ``state/id_map.json`` e devolve o mapa de ids.

    As chaves de um objeto JSON são sempre texto, então os ids do legado são
    convertidos de volta para inteiro ao carregar. Se o arquivo ainda não existir
    (primeira execução), devolve um dicionário vazio.
    """
    try:
        with open(_id_map_path(), encoding="utf-8") as file:
            raw_map = json.load(file)

    except FileNotFoundError:
        return {}

    return _normalize_id_map(raw_map)


def _normalize_id_map(raw_map: dict) -> dict:
    return {
        table: {
            int(legacy_id): new_id
            for legacy_id, new_id in mapping.items()
        }
        for table, mapping in raw_map.items()
    }


def load_database_id_map(connection) -> dict:
    """Carrega o estado durável e serializa as cargas na transação atual."""
    # O lock transacional também protege a criação e a primeira importação.
    connection.execute(text("SELECT pg_advisory_xact_lock(16481273)"))
    state_table = connection.execute(
        text("SELECT to_regclass('public.tb_rpa_state')")
    ).scalar_one_or_none()
    if state_table is None:
        connection.execute(text("""
            CREATE TABLE public.tb_rpa_state (
                id SMALLINT PRIMARY KEY CHECK (id = 1),
                id_map JSONB NOT NULL CHECK (jsonb_typeof(id_map) = 'object')
            )
        """))
    stored = connection.execute(
        text("SELECT id_map FROM public.tb_rpa_state WHERE id = 1 FOR UPDATE")
    ).scalar_one_or_none()
    if stored is not None:
        return _normalize_id_map(stored)

    # Compatibilidade: importa o JSON uma única vez, na primeira ativação.
    legacy_map = load_id_map()
    if not legacy_map and not os.path.isfile(_id_map_path()):
        log_table = connection.execute(
            text("SELECT to_regclass('public.tb_log_rpa')")
        ).scalar_one_or_none()
        if log_table is not None:
            previous_execution = connection.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM tb_log_rpa WHERE status IN ('SUCCESS', 'ERROR')
                )
            """)).scalar_one()
            if previous_execution:
                raise RuntimeError(
                    "Há execuções anteriores sem mapa de IDs recuperável. "
                    "Restaure o state/id_map.json antes da primeira ativação "
                    "do estado no banco; a carga foi cancelada para evitar duplicações."
                )
    return legacy_map


def save_database_id_map(connection, id_map: dict) -> None:
    """Grava o mapa dentro da mesma transação dos registros migrados."""
    connection.execute(text("""
        INSERT INTO public.tb_rpa_state (id, id_map)
        VALUES (1, CAST(:id_map AS JSONB))
        ON CONFLICT (id) DO UPDATE SET id_map = EXCLUDED.id_map
    """), {"id_map": json.dumps(id_map)})


def save_id_map(id_map: dict) -> None:
    """
    Grava o mapa de ids em ``state/id_map.json``.

    A gravação é feita primeiro em um arquivo temporário, que depois substitui o
    arquivo final. Assim, se a execução for interrompida no meio da escrita, o
    arquivo anterior não fica corrompido.
    """
    os.makedirs(STATE_DIRECTORY, exist_ok=True)

    serializable_map = {
        table: {
            str(legacy_id): new_id
            for legacy_id, new_id in mapping.items()
        }
        for table, mapping in id_map.items()
    }

    temporary_path = _id_map_path() + ".tmp"

    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(
            serializable_map,
            file,
            indent=2,
            ensure_ascii=False
        )

    os.replace(temporary_path, _id_map_path())
