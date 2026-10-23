import json

import pytest

from config import Config, ConfigError, Locator, load_config

SPEC_EXAMPLE = {
    "url": "https://exemplo.com/produto",
    "button": {"by": "text", "value": "Comprar"},
    "read_selectors": {"status": ".status", "preco": ".price"},
    "success_check": {"by": "text", "value": "Pedido confirmado"},
    "interval_seconds": 10,
    "after_click": "stop",
    "block_resources": ["image", "font", "media"],
    "restart_browser_every": 200,
    "headless": True,
}


def write(tmp_path, data):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def minimal(**overrides):
    data = {"url": "https://x.com", "button": {"by": "css", "value": "#b"}, "interval_seconds": 5}
    data.update(overrides)
    return data


def test_loads_spec_example(tmp_path):
    cfg = load_config(write(tmp_path, SPEC_EXAMPLE))
    assert isinstance(cfg, Config)
    assert cfg.button == Locator("text", "Comprar")
    assert cfg.interval_seconds == 10
    assert cfg.success_check == Locator("text", "Pedido confirmado")


def test_missing_file_raises_config_error(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nao-existe.json")


def test_invalid_json_raises_config_error(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ nao e json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_missing_url_raises_config_error(tmp_path):
    data = minimal()
    del data["url"]
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, data))


@pytest.mark.parametrize("value", [4.9, 0, -1])
def test_interval_below_5_raises_config_error(tmp_path, value):
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, minimal(interval_seconds=value)))


def test_invalid_after_click_raises_config_error(tmp_path):
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, minimal(after_click="pause")))


def test_invalid_locator_kind_raises_config_error(tmp_path):
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, minimal(button={"by": "xpath", "value": "//a"})))


def test_defaults(tmp_path):
    cfg = load_config(write(tmp_path, minimal()))
    assert cfg.block_resources == ("image", "font", "media")
    assert cfg.restart_browser_every == 200
    assert cfg.headless is True
    assert cfg.after_click == "stop"
    assert cfg.success_check is None
    assert cfg.read_selectors == {}
