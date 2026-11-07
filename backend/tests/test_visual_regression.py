"""Visual regression tests for Critique's homepage and auth screens.

These tests render real pages in Chromium and compare screenshots against
committed baselines. They are skipped when Playwright or Chromium is unavailable.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import shutil

try:
    from playwright.sync_api import sync_playwright
    _pw_ok = True
except Exception:
    _pw_ok = False
    sync_playwright = None

pytestmark = [
    pytest.mark.skipif(not _pw_ok, reason="playwright not installed"),
]

BASE_URL = os.environ.get("CRITIQUE_BASE_URL", "http://127.0.0.1:8099")
BASELINE_DIR = Path(__file__).resolve().parent / "visual_baselines"
VIEWPORTS = [375, 496, 511, 768, 1024, 1280, 1440]


def _server_ready():
    import urllib.request
    try:
        urllib.request.urlopen(BASE_URL + "/health", timeout=2)
        return True
    except Exception:
        return False


def _browser_available():
    if not _pw_ok:
        return False
    try:
        p = sync_playwright().start()
        b = p.chromium.launch()
        b.close()
        p.stop()
        return True
    except Exception:
        return False


def _start_server():
    """Start uvicorn if not already running; return process or None."""
    if _server_ready():
        return None
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8099"],
        cwd=str(Path(__file__).resolve().parent.parent),
        env={**os.environ, "GITHUB_CLIENT_ID": os.environ.get("GITHUB_CLIENT_ID", "ci-test-client-id")},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        if _server_ready():
            return proc
        time.sleep(0.5)
    proc.terminate()
    return None


def _compare_images(actual_path, baseline_path, tolerance=0.15):
    from PIL import Image
    if not baseline_path.exists():
        return "missing_baseline"
    a = Image.open(actual_path).convert("RGB")
    b = Image.open(baseline_path).convert("RGB")
    if a.size != b.size:
        return f"size_mismatch {a.size} vs {b.size}"
    import math
    diff = 0
    total = a.size[0] * a.size[1]
    pa = list(a.getdata())
    pb = list(b.getdata())
    for ca, cb in zip(pa, pb):
        if ca != cb:
            diff += 1
    ratio = diff / total
    if ratio > tolerance:
        return f"diff_ratio {ratio:.4f} > {tolerance}"
    return None


def test_homepage_no_horizontal_overflow():
    if not _browser_available():
        pytest.skip("chromium not available")
    proc = _start_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for w in VIEWPORTS:
                ctx = browser.new_context(viewport={"width": w, "height": 900})
                page = ctx.new_page()
                page.goto(BASE_URL + "/")
                page.wait_for_load_state("networkidle")
                overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
                assert not overflow, f"horizontal overflow at {w}px"
                ctx.close()
            browser.close()
    finally:
        if proc:
            proc.terminate()


def test_homepage_screenshot_regression():
    if not _browser_available():
        pytest.skip("chromium not available")
    proc = _start_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for w in VIEWPORTS:
                ctx = browser.new_context(viewport={"width": w, "height": 900})
                page = ctx.new_page()
                page.goto(BASE_URL + "/")
                page.wait_for_load_state("networkidle")
                path = BASELINE_DIR / f"homepage_{w}.png"
                actual = BASELINE_DIR / f"homepage_{w}_actual.png"
                page.screenshot(path=str(actual), full_page=False)
                result = _compare_images(actual, path)
                if result == "missing_baseline":
                    # First run: save as baseline
                    actual.rename(path)
                    print(f"Created baseline: {path}")
                elif result:
                    raise AssertionError(f"homepage {w}px: {result}")
                else:
                    actual.unlink(missing_ok=True)
                ctx.close()
            browser.close()
    finally:
        if proc:
            proc.terminate()


def test_myprojects_no_horizontal_overflow():
    if not _browser_available():
        pytest.skip("chromium not available")
    proc = _start_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for w in VIEWPORTS:
                ctx = browser.new_context(viewport={"width": w, "height": 900})
                page = ctx.new_page()
                page.goto(BASE_URL + "/my-projects")
                page.wait_for_load_state("networkidle")
                overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
                assert not overflow, f"horizontal overflow at {w}px on my-projects"
                ctx.close()
            browser.close()
    finally:
        if proc:
            proc.terminate()


def test_login_prompt_visible():
    if not _browser_available():
        pytest.skip("chromium not available")
    proc = _start_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 496, "height": 900})
            page = ctx.new_page()
            page.goto(BASE_URL + "/my-projects")
            page.wait_for_load_state("networkidle")
            # login prompt should be visible
            prompt = page.query_selector(".login-prompt")
            assert prompt is not None, "login prompt not rendered"
            # email button visible
            btn = page.query_selector(".login-prompt-actions .btn-secondary")
            assert btn is not None, "email button not rendered"
            box = btn.bounding_box()
            assert box and box["width"] > 0 and box["height"] > 0
            ctx.close()
            browser.close()
    finally:
        if proc:
            proc.terminate()
