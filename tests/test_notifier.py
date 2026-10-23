import logging

from notifier import notify_success


def test_logs_message(caplog):
    with caplog.at_level(logging.INFO):
        notify_success("Clique confirmado", beep=lambda f, d: None)
    assert "Clique confirmado" in caplog.text


def test_calls_beep():
    calls = []
    notify_success("ok", beep=lambda f, d: calls.append((f, d)))
    assert calls


def test_beep_failure_does_not_raise(caplog):
    def broken(f, d):
        raise RuntimeError("sem som")

    with caplog.at_level(logging.WARNING):
        notify_success("ok", beep=broken)
    assert "sem som" in caplog.text
