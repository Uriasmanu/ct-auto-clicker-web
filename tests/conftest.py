import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="module")
def chromium():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(chromium):
    context = chromium.new_context()
    page = context.new_page()
    yield page
    context.close()
