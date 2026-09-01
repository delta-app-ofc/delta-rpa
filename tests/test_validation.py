import pandas as pd

from modules.validation import validate_data


def test_rejects_underage_user():
    dataframes = {
        "tb_user": pd.DataFrame([
            {"id": 1, "name": "Adult", "email": "a@x.com", "birth_date": "1990-01-01"},
            {"id": 2, "name": "Minor", "email": "b@x.com", "birth_date": "2015-01-01"},
        ])
    }

    result = validate_data(dataframes)

    assert len(result["valid"]["tb_user"]) == 1
    assert result["valid"]["tb_user"].iloc[0]["email"] == "a@x.com"
    assert "tb_user" in result["errors"]


def test_rejects_value_outside_allowed_domain():
    dataframes = {
        "tb_property": pd.DataFrame([
            {"id": 1, "name": "House", "type": "CASA", "classification": "residencial", "address_id": 1},
            {"id": 2, "name": "Invalid", "type": "SOBRADO", "classification": "residencial", "address_id": 1},
        ])
    }

    result = validate_data(dataframes)

    assert len(result["valid"]["tb_property"]) == 1
    assert result["valid"]["tb_property"].iloc[0]["type"] == "CASA"


def test_rejects_date_that_is_not_first_day_of_month():
    dataframes = {
        "tb_last_water_bill": pd.DataFrame([
            {"id": 1, "user_id": 1, "month": "2026-07-01", "consumption": 10},
            {"id": 2, "user_id": 2, "month": "2026-07-15", "consumption": 12},
        ])
    }

    result = validate_data(dataframes)

    assert len(result["valid"]["tb_last_water_bill"]) == 1
    assert str(result["valid"]["tb_last_water_bill"].iloc[0]["month"]) == "2026-07-01"


def test_duplicate_records_are_all_removed():
    """
    Documents the current behavior: _validate_duplicates uses keep=False,
    so ALL rows with duplicate emails are removed (none survive), not only
    the extra occurrences.
    """
    dataframes = {
        "tb_user": pd.DataFrame([
            {"id": 1, "name": "A", "email": "dup@x.com", "birth_date": "1990-01-01"},
            {"id": 2, "name": "B", "email": "dup@x.com", "birth_date": "1991-01-01"},
            {"id": 3, "name": "C", "email": "unique@x.com", "birth_date": "1992-01-01"},
        ])
    }

    result = validate_data(dataframes)

    assert len(result["valid"]["tb_user"]) == 1
    assert result["valid"]["tb_user"].iloc[0]["email"] == "unique@x.com"


def test_invalid_foreign_key_is_reported():
    dataframes = {
        "tb_user": pd.DataFrame([
            {"id": 1, "name": "A", "email": "a@x.com", "birth_date": "1990-01-01"},
        ]),
        "tb_user_property": pd.DataFrame([
            {"id": 1, "user_id": 1, "property_id": 1},
            {"id": 2, "user_id": 999, "property_id": 1},  # non-existent user_id
        ]),
    }

    result = validate_data(dataframes)

    assert "foreign_keys" in result["errors"]
    assert (result["errors"]["foreign_keys"]["column"] == "user_id").any()