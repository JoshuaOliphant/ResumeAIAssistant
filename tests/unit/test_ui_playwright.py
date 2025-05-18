import os
import pytest

playwright = pytest.importorskip("playwright.sync_api", reason="playwright not installed")
from playwright.sync_api import sync_playwright


def test_index_page_renders():
    index_path = os.path.abspath(os.path.join("templates", "index.html"))
    assert os.path.exists(index_path)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{index_path}")
        assert "Resume Customization App" in page.content()
        browser.close()
