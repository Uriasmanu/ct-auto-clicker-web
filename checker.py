import logging

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator as PwLocator
from playwright.sync_api import Page

from config import Locator

log = logging.getLogger(__name__)

NOT_AVAILABLE = "N/A"
READ_TIMEOUT_MS = 2000


def locate(page: Page, loc: Locator) -> PwLocator:
    if loc.by == "css":
        return page.locator(loc.value).first
    if loc.by == "text":
        return page.get_by_text(loc.value).first
    role, _, name = loc.value.partition(":")
    if name:
        return page.get_by_role(role, name=name).first
    return page.get_by_role(role).first


def read_fields(page: Page, selectors: dict[str, str]) -> dict[str, str]:
    result = {}
    for name, selector in selectors.items():
        try:
            element = page.locator(selector).first
            result[name] = element.inner_text(timeout=READ_TIMEOUT_MS).strip()
        except PlaywrightError:
            result[name] = NOT_AVAILABLE
    return result


def is_button_available(page: Page, loc: Locator) -> bool:
    try:
        button = locate(page, loc)
        return button.count() > 0 and button.is_visible() and button.is_enabled()
    except PlaywrightError as exc:
        log.warning("Falha ao checar o botão: %s", exc)
        return False


def click_button(page: Page, loc: Locator, timeout_ms: int = 5000) -> bool:
    try:
        locate(page, loc).click(timeout=timeout_ms)
        return True
    except PlaywrightError as exc:
        log.warning("Falha ao clicar no botão: %s", exc)
        return False


def _is_visible(page: Page, loc: Locator) -> bool:
    try:
        element = locate(page, loc)
        return element.count() > 0 and element.is_visible()
    except PlaywrightError:
        return False


def confirm_success(page: Page, check: Locator | None, old_url: str, button: Locator) -> bool:
    if check is not None:
        try:
            locate(page, check).wait_for(state="visible", timeout=3000)
            return True
        except PlaywrightError:
            pass
    return page.url != old_url or not _is_visible(page, button)
