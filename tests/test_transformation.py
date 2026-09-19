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