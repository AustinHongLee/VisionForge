from visionforge_app.api import __main__ as api_main


def test_parent_pid_env_is_optional(monkeypatch) -> None:
    monkeypatch.delenv("VISIONFORGE_PARENT_PID", raising=False)

    assert api_main._parent_pid() is None


def test_parent_pid_env_rejects_invalid_values(monkeypatch) -> None:
    monkeypatch.setenv("VISIONFORGE_PARENT_PID", "not-a-pid")

    assert api_main._parent_pid() is None


def test_parent_pid_env_accepts_positive_integer(monkeypatch) -> None:
    monkeypatch.setenv("VISIONFORGE_PARENT_PID", "12345")

    assert api_main._parent_pid() == 12345
