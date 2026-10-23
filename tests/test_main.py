import json
from dataclasses import replace

import pytest
from playwright.sync_api import Error as PlaywrightError

import main
from browser import BrowserSession
from config import Config, Locator

BUTTON_PAGE = (
    "<div class='status'>ok</div>"
    "<button {attrs} onclick=\"document.body.innerHTML='<p>Pedido confirmado</p>'\">Comprar</button>"
)


@pytest.fixture
def cfg():
    return Config(
        url="http://127.0.0.1:1/",
        button=Locator("text", "Comprar"),
        interval_seconds=20,
        read_selectors={"status": ".status"},
        success_check=Locator("text", "Pedido confirmado"),
    )


@pytest.fixture
def session(cfg):
    s = BrowserSession(cfg)
    s.start()
    yield s
    s.close()


class FakeSession:
    def __init__(self, goto_failures=0, reload_failures=0):
        self.goto_failures = goto_failures
        self.reload_failures = reload_failures
        self.gotos = self.reloads = self.restarts = 0
        self.closed = False
        self.started = False

    def start(self):
        self.started = True

    def goto(self):
        self.gotos += 1
        if self.goto_failures > 0:
            self.goto_failures -= 1
            raise PlaywrightError("net::ERR_INTERNET_DISCONNECTED")

    def reload(self):
        self.reloads += 1
        if self.reload_failures > 0:
            self.reload_failures -= 1
            raise PlaywrightError("net::ERR_INTERNET_DISCONNECTED")

    def restart(self):
        self.restarts += 1

    def close(self):
        self.closed = True


def test_next_backoff_doubles_and_caps():
    value, seen = 0.0, []
    for _ in range(9):
        value = main.next_backoff(value)
        seen.append(value)
    assert seen == [5, 10, 20, 40, 80, 160, 300, 300, 300]


def test_main_returns_2_on_config_error(tmp_path, capsys):
    code = main.main(["--config", str(tmp_path / "nao-existe.json")])
    assert code == 2
    assert "não encontrado" in capsys.readouterr().err


def test_run_cycle_unavailable_when_button_disabled(session, cfg):
    session.page.set_content(BUTTON_PAGE.format(attrs="disabled"))
    assert main.run_cycle(session, cfg) == "unavailable"
    assert session.page.get_by_text("Pedido confirmado").count() == 0


def test_run_cycle_clicks_and_confirms(session, cfg, monkeypatch):
    notified = []
    monkeypatch.setattr(main, "notify_success", notified.append)
    session.page.set_content(BUTTON_PAGE.format(attrs=""))
    assert main.run_cycle(session, cfg) == "clicked"
    assert len(notified) == 1


def test_run_cycle_reports_unavailable_when_click_fails(session, cfg, monkeypatch):
    session.page.set_content(BUTTON_PAGE.format(attrs=""))
    monkeypatch.setattr(main, "click_button", lambda *a, **k: False)
    assert main.run_cycle(session, cfg) == "unavailable"


def test_loop_stops_after_click_when_after_click_stop(cfg, monkeypatch):
    monkeypatch.setattr(main, "run_cycle", lambda s, c: "clicked")
    session = FakeSession()
    main.monitor(session, cfg, sleep=lambda s: None, max_cycles=5)
    assert session.gotos == 1 and session.reloads == 0


def test_loop_continues_when_after_click_continue(cfg, monkeypatch):
    monkeypatch.setattr(main, "run_cycle", lambda s, c: "clicked")
    session = FakeSession()
    main.monitor(session, replace(cfg, after_click="continue"), sleep=lambda s: None, max_cycles=4)
    assert session.gotos == 1 and session.reloads == 3


def test_loop_survives_network_error_and_backs_off(cfg, monkeypatch):
    monkeypatch.setattr(main, "run_cycle", lambda s, c: "unavailable")
    session = FakeSession(goto_failures=2)
    sleeps = []
    main.monitor(session, cfg, sleep=sleeps.append, max_cycles=3)
    assert sleeps == [5, 10, 20]


def test_loop_survives_reload_error(cfg, monkeypatch):
    monkeypatch.setattr(main, "run_cycle", lambda s, c: "unavailable")
    session = FakeSession(reload_failures=1)
    sleeps = []
    main.monitor(session, cfg, sleep=sleeps.append, max_cycles=3)
    assert sleeps == [20, 5, 20]


def test_browser_restarts_every_n_cycles(cfg, monkeypatch):
    monkeypatch.setattr(main, "run_cycle", lambda s, c: "unavailable")
    session = FakeSession()
    main.monitor(session, replace(cfg, restart_browser_every=3), sleep=lambda s: None, max_cycles=7)
    assert session.restarts == 2


def test_keyboard_interrupt_closes_browser_and_returns_0(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"url": "http://x", "button": {"by": "css", "value": "b"}, "interval_seconds": 5}),
        encoding="utf-8",
    )
    fake = FakeSession()
    monkeypatch.setattr(main, "BrowserSession", lambda cfg: fake)
    monkeypatch.setattr(main, "setup_logging", lambda *a, **k: None)

    def interrupt(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(main, "monitor", interrupt)
    assert main.main(["--config", str(path)]) == 0
    assert fake.started and fake.closed
