import pandas as pd

from modules.transformation import transform_data


def test_converts_city_and_state_to_uppercase():
    dataframes = {
        "tb_address": pd.DataFrame([
            {"id": 1, "city": "sao paulo", "state": "sp", "region_id": 1},
        ])
    }

    result = transform_data(dataframes)

    row = result["tb_address"].iloc[0]
    assert row["city"] == "SAO PAULO"
    assert row["state"] == "SP"


def test_replaces_apartment_with_building_and_keeps_house():
    dataframes = {
        "tb_property": pd.DataFrame([
            {"id": 1, "name": "a", "type": "APARTAMENTO", "classification": "residencial", "address_id": 1},
            {"id": 2, "name": "b", "type": "CASA", "classification": "residencial", "address_id": 1},
        ])
    }

    result = transform_data(dataframes)

    types = list(result["tb_property"]["type"])
    assert types == ["PRÉDIO", "CASA"]


def test_maps_classification_to_the_new_lookup_id():
    dataframes = {
        "tb_property": pd.DataFrame([
            {"id": 1, "name": "a", "type": "CASA", "classification": "residencial", "address_id": 1},
            {"id": 2, "name": "b", "type": "CASA", "classification": "comercial", "address_id": 1},
        ])
    }

    result = transform_data(dataframes)

    assert "classification" not in result["tb_property"].columns
    assert list(result["tb_property"]["classification_id"]) == [1, 5]


def test_table_without_rules_remains_unchanged():
    dataframes = {
        "tb_region_rate": pd.DataFrame([
            {"id": 1, "region_id": 1, "m3_value": 12.5, "initial_validity": "2026-01-01"},
        ])
    }

    result = transform_data(dataframes)

    pd.testing.assert_frame_equal(
        result["tb_region_rate"],
        dataframes["tb_region_rate"]
    )


def test_device_id_is_converted_to_string():
    dataframes = {
        "tb_device": pd.DataFrame([
            {"id": 1, "device_id": 1001, "property_id": 2},
        ])
    }

    result = transform_data(dataframes)

    value = result["tb_device"].iloc[0]["device_id"]
    assert value == "1001"
    assert isinstance(value, str)

def test_hashes_user_password_with_argon2id():
    dataframes = {
        "tb_user": pd.DataFrame([
            {"id": 1, "name": "a", "email": "a@a.com", "password": "senha123"},
            {"id": 2, "name": "b", "email": "b@a.com", "password": "$argon2id$ja-hasheada"},
        ])
    }

    result = transform_data(dataframes)["tb_user"]

    assert result.iloc[0]["password"].startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert "senha123" not in result.iloc[0]["password"]
    assert result.iloc[1]["password"] == "$argon2id$ja-hasheada"


def test_formats_phone_as_brazilian_mask():
    dataframes = {
        "tb_user": pd.DataFrame([
            {"id": 1, "name": "a", "email": "a@a.com", "password": "x", "phone": "11911551155"},
            {"id": 2, "name": "b", "email": "b@a.com", "password": "x", "phone": "1131551155"},
            {"id": 3, "name": "c", "email": "c@a.com", "password": "x", "phone": "(11) 91155-1155"},
        ])
    }

    result = transform_data(dataframes)["tb_user"]

    assert list(result["phone"]) == ["(11) 91155-1155", "(11) 3155-1155", "(11) 91155-1155"]
