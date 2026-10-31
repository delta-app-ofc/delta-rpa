import pandas as pd
import pytest

import main


def _prepare_pipeline(monkeypatch, *, extraction, validation, transformed, load_counts):
    monkeypatch.setattr(main, "get_logger", lambda: object())
    monkeypatch.setattr(main, "log_start", lambda logger: None)
    monkeypatch.setattr(main, "log_end", lambda logger: None)
    monkeypatch.setattr(main, "log_extraction", lambda *args: None)
    monkeypatch.setattr(main, "log_validation", lambda *args: None)
    monkeypatch.setattr(main, "log_transformation", lambda *args: None)
    monkeypatch.setattr(main, "start_execution_log", lambda: 71)
    monkeypatch.setattr(main, "find_tables", lambda tables: extraction)
    monkeypatch.setattr(main, "validate_data", lambda data: validation)
    monkeypatch.setattr(main, "transform_data", lambda data: transformed)
    monkeypatch.setattr(main, "load_data", lambda data, ids: load_counts)


def test_build_extracted_ids_ignores_tables_without_ids_and_null_ids():
    extracted = {
        "tb_user": pd.DataFrame({"id": [1, 2, 2, None]}),
        "reference": pd.DataFrame({"name": ["fixed"]}),
    }

    assert main._build_extracted_ids(extracted) == {"tb_user": {1, 2}}


def test_main_records_success_counts_and_validation_errors(monkeypatch):
    extracted = {
        "tb_user": pd.DataFrame({"id": [1, 2], "email": ["a@test", "b@test"]})
    }
    errors = {"tb_user": pd.DataFrame({"index": [1, 2]})}
    validation = {"valid": extracted, "errors": errors}
    load_counts = {
        "tb_user": {"inserted": 2, "updated": 1, "deleted": 3}
    }
    _prepare_pipeline(
        monkeypatch,
        extraction=extracted,
        validation=validation,
        transformed=extracted,
        load_counts=load_counts,
    )
    finished = []
    monkeypatch.setattr(
        main, "finish_execution_log", lambda *args: finished.append(args)
    )

    main.main()

    assert finished == [("71", "SUCCESS", 2, 1, 3, 2, None)] or finished == [
        (71, "SUCCESS", 2, 1, 3, 2, None)
    ]


def test_main_reraises_pipeline_failure_and_persists_error_status(monkeypatch):
    extracted = {"tb_user": pd.DataFrame({"id": [1]})}
    validation = {"valid": extracted, "errors": {}}
    _prepare_pipeline(
        monkeypatch,
        extraction=extracted,
        validation=validation,
        transformed=extracted,
        load_counts={},
    )
    failure = ValueError("transform failed")
    monkeypatch.setattr(main, "transform_data", lambda data: (_ for _ in ()).throw(failure))
    errors_logged = []
    monkeypatch.setattr(
        main,
        "log_error",
        lambda logger, message, error: errors_logged.append((message, error)),
    )
    finished = []
    monkeypatch.setattr(
        main,
        "finish_execution_log",
        lambda *args: finished.append(args),
    )

    with pytest.raises(ValueError, match="transform failed"):
        main.main()

    assert finished[0][:6] == (71, "ERROR", 0, 0, 0, 0)
    assert finished[0][6] == "transform failed"
    assert errors_logged[0][1] is failure


def test_main_does_not_hide_pipeline_error_if_final_log_also_fails(monkeypatch):
    extracted = {"tb_user": pd.DataFrame({"id": [1]})}
    validation = {"valid": extracted, "errors": {}}
    _prepare_pipeline(
        monkeypatch,
        extraction=extracted,
        validation=validation,
        transformed=extracted,
        load_counts={},
    )
    failure = ValueError("load failed")
    monkeypatch.setattr(main, "load_data", lambda *args: (_ for _ in ()).throw(failure))
    log_failures = []
    monkeypatch.setattr(
        main,
        "log_error",
        lambda logger, message, error: log_failures.append((message, error)),
    )

    def fail_final_log(*args):
        raise RuntimeError("log database unavailable")

    monkeypatch.setattr(main, "finish_execution_log", fail_final_log)

    with pytest.raises(ValueError, match="load failed"):
        main.main()

    assert [message for message, _ in log_failures] == [
        "Erro durante a execução do RPA",
        "Falha ao gravar o fim da execução em tb_log_rpa",
    ]
