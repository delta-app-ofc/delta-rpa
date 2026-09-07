import json

from modules.state import load_id_map, save_id_map


def test_load_returns_empty_dict_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert load_id_map() == {}


def test_save_then_load_round_trips_with_int_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    id_map = {
        "tb_user": {1: 10, 2: 11},
        "tb_address": {5: 50},
    }

    save_id_map(id_map)

    loaded = load_id_map()

    assert loaded == id_map
    # As chaves do legado precisam voltar como inteiro, não como texto.
    assert all(
        isinstance(legacy_id, int)
        for mapping in loaded.values()
        for legacy_id in mapping
    )


def test_saved_file_is_valid_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    save_id_map({"tb_user": {1: 10}})

    content = (tmp_path / "state" / "id_map.json").read_text(encoding="utf-8")

    assert json.loads(content) == {"tb_user": {"1": 10}}
