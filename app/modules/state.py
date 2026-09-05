"""
Persistência do mapa de ids entre execuções do RPA.

O mapa de ids relaciona o id de cada registro no banco legado com o id que ele
recebeu no banco novo, no formato:

    {
        "tb_user": { 1: 10, 2: 11 },
        "tb_address": { 1: 5 },
        ...
    }

Ele é gravado em ``state/id_map.json`` ao final de cada carga bem-sucedida e lido
no início da execução seguinte. É a partir desse arquivo que o RPA sabe quais
registros do legado já foram migrados (para decidir entre inserir e atualizar) e
quais foram apagados no legado (para replicar a exclusão no banco novo).
"""

import json
import os


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

    id_map = {}

    for table, mapping in raw_map.items():

        id_map[table] = {
            int(legacy_id): new_id
            for legacy_id, new_id in mapping.items()
        }

    return id_map


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
