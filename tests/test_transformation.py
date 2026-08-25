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


def test_table_without_rules_remains_unchanged():
    dataframes = {
        "tb_region_rate": pd.DataFrame([
            {"id": 1, "region_id": 1, "rate": 12.5},
        ])
    }

    result = transform_data(dataframes)

    pd.testing.assert_frame_equal(
        result["tb_region_rate"],
        dataframes["tb_region_rate"]
    )