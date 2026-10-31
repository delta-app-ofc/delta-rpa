from modules import execution_log


class FakeResult:
    def scalar_one(self):
        return 42


class FakeConnection:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, statement, parameters=None):
        self.calls.append((str(statement), parameters))
        return FakeResult()


class FakeEngine:
    def __init__(self):
        self.connection = FakeConnection()
        self.begin_calls = 0

    def begin(self):
        self.begin_calls += 1
        return self.connection


def test_start_execution_log_inserts_running_row(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(
        execution_log, "create_second_year_connection", lambda: engine
    )

    result = execution_log.start_execution_log()

    query, parameters = engine.connection.calls[0]
    assert result == 42
    assert "INSERT INTO tb_log_rpa (status)" in query
    assert "VALUES ('RUNNING')" in query
    assert parameters is None


def test_finish_execution_log_skips_missing_id(monkeypatch):
    opened = []
    monkeypatch.setattr(
        execution_log,
        "create_second_year_connection",
        lambda: opened.append(True),
    )

    execution_log.finish_execution_log(None, "ERROR", 0, 0, 0, 0)

    assert opened == []


def test_finish_execution_log_writes_final_counts_and_message(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(
        execution_log, "create_second_year_connection", lambda: engine
    )

    execution_log.finish_execution_log(42, "ERROR", 2, 3, 1, 4, "falha")

    query, parameters = engine.connection.calls[0]
    assert "UPDATE tb_log_rpa" in query
    assert "finished_at = CURRENT_TIMESTAMP" in query
    assert parameters == {
        "status": "ERROR",
        "inserted_count": 2,
        "updated_count": 3,
        "deleted_count": 1,
        "validation_error_count": 4,
        "error_message": "falha",
        "log_id": 42,
    }
