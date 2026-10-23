import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

MIN_INTERVAL_SECONDS = 5
LOCATOR_KINDS = ("css", "text", "role")
AFTER_CLICK_MODES = ("stop", "continue")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Locator:
    by: Literal["css", "text", "role"]
    value: str


@dataclass(frozen=True)
class Config:
    url: str
    button: Locator
    interval_seconds: float
    read_selectors: dict[str, str] = field(default_factory=dict)
    success_check: Locator | None = None
    after_click: Literal["stop", "continue"] = "stop"
    block_resources: tuple[str, ...] = ("image", "font", "media")
    restart_browser_every: int = 200
    headless: bool = True


def _parse_locator(raw, name: str) -> Locator:
    if not isinstance(raw, dict):
        raise ConfigError(f"'{name}' deve ser um objeto com 'by' e 'value'")
    by, value = raw.get("by"), raw.get("value")
    if by not in LOCATOR_KINDS:
        raise ConfigError(f"'{name}.by' deve ser um de {', '.join(LOCATOR_KINDS)}")
    if not isinstance(value, str) or not value:
        raise ConfigError(f"'{name}.value' deve ser um texto não vazio")
    return Locator(by, value)


def _number(data: dict, key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"'{key}' deve ser um número")
    return value


def load_config(path: str | Path) -> Config:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"Arquivo de configuração não encontrado: {path}") from None
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise ConfigError(f"Não foi possível ler {path}: {exc}") from None
    if not isinstance(data, dict):
        raise ConfigError("O config.json deve ser um objeto JSON")

    url = data.get("url")
    if not isinstance(url, str) or not url:
        raise ConfigError("'url' é obrigatório")
    if "button" not in data:
        raise ConfigError("'button' é obrigatório")

    interval = _number(data, "interval_seconds")
    if interval < MIN_INTERVAL_SECONDS:
        raise ConfigError(f"'interval_seconds' deve ser no mínimo {MIN_INTERVAL_SECONDS}")

    after_click = data.get("after_click", "stop")
    if after_click not in AFTER_CLICK_MODES:
        raise ConfigError(f"'after_click' deve ser um de {', '.join(AFTER_CLICK_MODES)}")

    read_selectors = data.get("read_selectors", {})
    if not isinstance(read_selectors, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in read_selectors.items()
    ):
        raise ConfigError("'read_selectors' deve mapear nomes para seletores CSS")

    restart_every = data.get("restart_browser_every", 200)
    if isinstance(restart_every, bool) or not isinstance(restart_every, int) or restart_every < 1:
        raise ConfigError("'restart_browser_every' deve ser um inteiro maior que 0")

    success_raw = data.get("success_check")
    return Config(
        url=url,
        button=_parse_locator(data["button"], "button"),
        interval_seconds=interval,
        read_selectors=read_selectors,
        success_check=_parse_locator(success_raw, "success_check") if success_raw else None,
        after_click=after_click,
        block_resources=tuple(data.get("block_resources", ("image", "font", "media"))),
        restart_browser_every=restart_every,
        headless=bool(data.get("headless", True)),
    )
