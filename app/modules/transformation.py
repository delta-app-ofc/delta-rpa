import unicodedata

import pandas as pd
from argon2 import PasswordHasher

# Mesmos parâmetros do Argon2PasswordEncoder da delta-api-postgres
# (SecurityConfig): salt 16, hash 32, paralelismo 1, 19456 KiB, 2 iterações.
_PASSWORD_HASHER = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    salt_len=16
)

# O banco do primeiro ano não guarda latitude/longitude, mas tb_address no banco
# novo exige as duas (NOT NULL). Sem serviço externo, usamos o centro da cidade.
# Cidades fora da lista caem no centro de São Paulo (DEFAULT_COORDINATES).
CITY_COORDINATES = {
    "SAO PAULO": (-23.550520, -46.633308),
    "GUARULHOS": (-23.453800, -46.533300),
    "OSASCO": (-23.532900, -46.791700),
    "BRAGANCA PAULISTA": (-22.952700, -46.541900),
    "PRESIDENTE PRUDENTE": (-22.120700, -51.392500),
    "ADAMANTINA": (-21.682000, -51.068900),
    "LINS": (-21.678600, -49.742400),
    "CURITIBA": (-25.428400, -49.273300),
    "PORTO ALEGRE": (-30.034600, -51.217700),
    "BRASILIA": (-15.794200, -47.882200)
}

DEFAULT_COORDINATES = CITY_COORDINATES["SAO PAULO"]

TRANSFORMATIONS = {

    "tb_address": {
        "coordinates": True,

        "uppercase": [
            "city",
            "state"
        ],

        # No legado as regiões são zonas de São Paulo (ZONA LESTE, CENTRO,
        # ZONA NORTE). No banco novo a região define a tarifa, e todas essas
        # zonas pertencem a GRANDE_SP (id 1).
        "replace": {
            "region_id": {
                4: 1,
                12: 1,
                13: 1
            }
        }
    },

    "tb_user": {
        "uppercase": [
            "name",
            "email"
        ],

        "argon2": [
            "password"
        ],

        "phone": [
            "phone"
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


def _normalize_city(city) -> str:
    """Tira acentos e deixa em maiúsculas para casar com CITY_COORDINATES."""
    text = unicodedata.normalize("NFKD", str(city))
    text = "".join(char for char in text if not unicodedata.combining(char))

    return text.strip().upper()


def _transform_coordinates(
    dataframe: pd.DataFrame
):
    """
    Preenche latitude e longitude pelo centro da cidade quando vierem vazias.

    Valores já preenchidos no legado são mantidos.
    """
    dataframe = dataframe.copy()

    if "city" not in dataframe.columns:
        return dataframe

    for column in ("latitude", "longitude"):
        if column not in dataframe.columns:
            dataframe[column] = None

        dataframe[column] = dataframe[column].astype("object")

    for index, city in dataframe["city"].items():
        latitude, longitude = CITY_COORDINATES.get(
            _normalize_city(city),
            DEFAULT_COORDINATES
        )

        if pd.isna(dataframe.at[index, "latitude"]):
            dataframe.at[index, "latitude"] = latitude

        if pd.isna(dataframe.at[index, "longitude"]):
            dataframe.at[index, "longitude"] = longitude

    return dataframe


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

def _transform_argon2(
    dataframe: pd.DataFrame,
    columns: list[str]
):
    """
    Troca a senha em texto puro do legado por um hash Argon2id.

    Valores que já começam com ``$argon2`` são mantidos, para não gerar
    hash de um hash caso o legado passe a guardá-lo assim.
    """
    dataframe = dataframe.copy()

    def _hash(value):
        if not isinstance(value, str) or value.startswith("$argon2"):
            return value

        return _PASSWORD_HASHER.hash(value)

    for column in columns:

        if column not in dataframe.columns:
            continue

        dataframe[column] = dataframe[column].map(_hash).astype("object")

    return dataframe


def _transform_phone(
    dataframe: pd.DataFrame,
    columns: list[str]
):
    """
    Formata telefone só com dígitos como (11) 91155-1155 (celular, 11 dígitos)
    ou (11) 1155-1155 (fixo, 10 dígitos). Outros formatos ficam como estão.
    """
    dataframe = dataframe.copy()

    def _format(value):
        if not isinstance(value, str):
            return value

        digits = "".join(char for char in value if char.isdigit())

        if len(digits) == 11:
            return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"

        if len(digits) == 10:
            return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"

        return value

    for column in columns:

        if column not in dataframe.columns:
            continue

        dataframe[column] = dataframe[column].map(_format).astype("object")

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

    if rules.get("coordinates"):
        transformed = _transform_coordinates(transformed)

    transformed = _transform_uppercase(
        transformed,
        rules.get("uppercase", [])
    )

    transformed = _transform_argon2(
        transformed,
        rules.get("argon2", [])
    )

    transformed = _transform_phone(
        transformed,
        rules.get("phone", [])
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
