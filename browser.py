from playwright.sync_api import Browser, BrowserContext, Page, Playwright, Route, sync_playwright

from config import Config

CHROMIUM_ARGS = [
    "--disable-gpu",
    "--disable-extensions",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]
NAVIGATION_TIMEOUT_MS = 30000


def should_block(resource_type: str, blocked: tuple[str, ...]) -> bool:
    return resource_type in blocked


class BrowserSession:
    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Navegador não iniciado")
        return self._page

    def start(self) -> Page:
        self._playwright = sync_playwright().start()
        try:
            self._browser = self._playwright.chromium.launch(
                headless=self._cfg.headless, args=CHROMIUM_ARGS
            )
            self._context = self._browser.new_context()
            self._context.route("**/*", self._handle_route)
            self._page = self._context.new_page()
            self._page.set_default_timeout(NAVIGATION_TIMEOUT_MS)
        except Exception:
            self.close()
            raise
        return self._page

    def _handle_route(self, route: Route) -> None:
        if should_block(route.request.resource_type, self._cfg.block_resources):
            route.abort()
        else:
            route.continue_()

    def goto(self) -> None:
        self.page.goto(self._cfg.url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)

    def reload(self) -> None:
        self.page.reload(wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)

    def restart(self) -> Page:
        self.close()
        page = self.start()
        self.goto()
        return page

    def close(self) -> None:
        for closer in (
            lambda: self._browser and self._browser.close(),
            lambda: self._playwright and self._playwright.stop(),
        ):
            try:
                closer()
            except Exception:
                pass
        self._playwright = self._browser = self._context = self._page = None
