import argparse
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Literal

from browser import BrowserSession
from checker import click_button, confirm_success, is_button_available, read_fields
from config import Config, ConfigError, load_config
from notifier import notify_success

log = logging.getLogger("auto-clicker")

BACKOFF_BASE_SECONDS = 5
BACKOFF_CAP_SECONDS = 300
FAILURES_BEFORE_BROWSER_RESTART = 3
LOG_MAX_BYTES = 1_000_000
LOG_BACKUPS = 3


def setup_logging(log_dir: Path = Path("logs")) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handlers = [
        RotatingFileHandler(
            log_dir / "auto-clicker.log",
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUPS,
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ]
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in handlers:
        handler.setFormatter(fmt)
        root.addHandler(handler)


def next_backoff(
    current: float, base: float = BACKOFF_BASE_SECONDS, cap: float = BACKOFF_CAP_SECONDS
) -> float:
    return base if current <= 0 else min(current * 2, cap)


def run_cycle(session: BrowserSession, cfg: Config) -> Literal["clicked", "unavailable"]:
    page = session.page
    fields = read_fields(page, cfg.read_selectors)
    if fields:
        log.info("Campos: %s", " | ".join(f"{k}={v}" for k, v in fields.items()))
    if not is_button_available(page, cfg.button):
        log.info("Botão indisponível")
        return "unavailable"

    log.info("Botão disponível, clicando")
    old_url = page.url
    if not click_button(page, cfg.button):
        return "unavailable"
    if confirm_success(page, cfg.success_check, old_url, cfg.button):
        notify_success("Clique realizado e sucesso confirmado")
    else:
        log.warning("Clique realizado, mas o sucesso não foi confirmado")
    return "clicked"


def monitor(
    session: BrowserSession,
    cfg: Config,
    sleep: Callable[[float], None] = time.sleep,
    max_cycles: int | None = None,
) -> None:
    backoff = 0.0
    failures = 0
    checks = 0
    loaded = False
    needs_restart = False
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        cycles += 1
        try:
            if needs_restart or checks >= cfg.restart_browser_every:
                log.info("Reiniciando o navegador")
                session.restart()
                checks, needs_restart = 0, False
            elif not loaded:
                session.goto()
            else:
                session.reload()
            loaded = True
            result = run_cycle(session, cfg)
        except Exception as exc:
            failures += 1
            loaded = False
            needs_restart = failures % FAILURES_BEFORE_BROWSER_RESTART == 0
            backoff = next_backoff(backoff)
            reason = (str(exc).splitlines() or [type(exc).__name__])[0]
            log.warning("Falha (%s); nova tentativa em %.0fs", reason, backoff)
            sleep(backoff)
            continue

        failures, backoff = 0, 0.0
        checks += 1
        if result == "clicked" and cfg.after_click == "stop":
            log.info("Encerrando após o clique")
            return
        sleep(cfg.interval_seconds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clica em um botão assim que ele fica disponível")
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        return 2

    setup_logging()
    session = BrowserSession(cfg)
    try:
        session.start()
        monitor(session, cfg)
    except KeyboardInterrupt:
        log.info("Interrompido pelo usuário")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
