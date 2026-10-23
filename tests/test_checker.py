from checker import click_button, confirm_success, is_button_available, locate, read_fields
from config import Locator

BTN = Locator("text", "Comprar")


def test_available_when_visible_and_enabled(page):
    page.set_content("<button>Comprar</button>")
    assert is_button_available(page, BTN) is True


def test_unavailable_when_disabled(page):
    page.set_content("<button disabled>Comprar</button>")
    assert is_button_available(page, BTN) is False


def test_unavailable_when_hidden(page):
    page.set_content('<button style="display:none">Comprar</button>')
    assert is_button_available(page, BTN) is False


def test_unavailable_when_absent(page):
    page.set_content("<p>nada</p>")
    assert is_button_available(page, BTN) is False


def test_locate_by_text_css_and_role(page):
    page.set_content('<button id="b">Comprar</button>')
    for loc in (
        Locator("text", "Comprar"),
        Locator("css", "#b"),
        Locator("role", "button:Comprar"),
        Locator("role", "button"),
    ):
        assert locate(page, loc).text_content() == "Comprar"


def test_read_fields_returns_text_and_na_for_missing(page):
    page.set_content('<div class="status"> Em estoque </div>')
    result = read_fields(page, {"status": ".status", "x": ".nao-existe"})
    assert result == {"status": "Em estoque", "x": "N/A"}


def test_click_button_triggers_handler(page):
    page.set_content(
        "<button onclick=\"document.body.insertAdjacentHTML('beforeend','<p>clicou</p>')\">Comprar</button>"
    )
    assert click_button(page, BTN) is True
    assert page.get_by_text("clicou").count() == 1


def test_click_button_returns_false_when_missing(page):
    page.set_content("<p>nada</p>")
    assert click_button(page, BTN, timeout_ms=300) is False


def test_confirm_success_by_text(page):
    page.set_content("<button>Comprar</button><p>Pedido confirmado</p>")
    assert confirm_success(page, Locator("text", "Pedido confirmado"), page.url, BTN) is True


def test_confirm_success_by_button_gone(page):
    page.set_content("<p>sem botao</p>")
    assert confirm_success(page, None, page.url, BTN) is True


def test_confirm_success_false_when_nothing_changed(page):
    page.set_content("<button>Comprar</button>")
    assert confirm_success(page, Locator("text", "Pedido confirmado"), page.url, BTN) is False
