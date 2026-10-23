import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from browser import BrowserSession, should_block
from config import Config, Locator

PAGE = b'<html><body><p id="t">ola</p><img src="/pixel.png"></body></html>'
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000002000001e221bc330000000049454e44ae426082"
)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body, kind = (PNG, "image/png") if self.path.endswith(".png") else (PAGE, "text/html")
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def server_url():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()


@pytest.fixture
def cfg(server_url):
    return Config(url=server_url, button=Locator("css", "#t"), interval_seconds=5)


def test_should_block_matches_only_listed_types():
    blocked = ("image", "font", "media")
    assert all(should_block(t, blocked) for t in blocked)
    assert not any(should_block(t, blocked) for t in ("document", "script"))


def test_start_opens_single_page_in_single_context(cfg):
    session = BrowserSession(cfg)
    page = session.start()
    try:
        assert len(page.context.browser.contexts) == 1
        assert len(page.context.pages) == 1
    finally:
        session.close()


def test_images_are_blocked(cfg):
    session = BrowserSession(cfg)
    page = session.start()
    failed = []
    page.on("requestfailed", lambda r: failed.append(r.resource_type))
    try:
        session.goto()
        page.wait_for_load_state("load")
        assert "image" in failed
    finally:
        session.close()


def test_restart_returns_working_page(cfg):
    session = BrowserSession(cfg)
    session.start()
    session.goto()
    try:
        page = session.restart()
        assert page.locator("#t").inner_text() == "ola"
    finally:
        session.close()


def test_reload_keeps_page_working(cfg):
    session = BrowserSession(cfg)
    session.start()
    session.goto()
    try:
        session.reload()
        assert session.page.locator("#t").inner_text() == "ola"
    finally:
        session.close()


def test_close_is_idempotent(cfg):
    session = BrowserSession(replace(cfg))
    session.start()
    session.close()
    session.close()
