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
                    if os.environ.get("GENERATE_VISUAL_BASELINES") == "1":
                        actual.rename(path)
                        print(f"Created baseline: {path}")
                    else:
                        actual.unlink(missing_ok=True)
                        raise AssertionError(
                            f"homepage {w}px: missing baseline screenshot {path.name}. "
                            "Run with GENERATE_VISUAL_BASELINES=1 to create it intentionally."
                        )
                elif result:
                    actual.unlink(missing_ok=True)
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


@pytest.fixture(scope="module")
def auth_visual_browser():
    """Reuse one local server and Chromium process for the auth-state matrix."""
    if not _browser_available():
        pytest.skip("chromium not available")
    proc = _start_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            yield browser
            browser.close()
    finally:
        if proc:
            proc.terminate()


def _auth_page(browser, width):
    context = browser.new_context(
        viewport={"width": width, "height": 900},
        reduced_motion="reduce",
    )
    page = context.new_page()
    page.route(
        "**/auth/check",
        lambda route: route.fulfill(
            status=401,
            content_type="application/json",
            body='{"detail":"Not authenticated"}',
        ),
    )
    page.route(
        "**/api/projects/my/list",
        lambda route: route.fulfill(
            status=401,
            content_type="application/json",
            body='{"detail":"Not authenticated"}',
        ),
    )
    # A test click on the GitHub option must never start the real OAuth flow.
    page.route("**/auth/login*", lambda route: route.abort())
    page.goto(BASE_URL + "/my-projects", wait_until="networkidle")
    page.locator(".login-prompt").wait_for()
    return context, page


def _auth_snapshot(page, state, width):
    overflow = page.evaluate(
        "document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert not overflow, f"horizontal overflow in {state} at {width}px"

    path = BASELINE_DIR / f"auth_{state}_{width}.png"
    actual = BASELINE_DIR / f"auth_{state}_{width}_actual.png"
    page.screenshot(path=str(actual), full_page=False, animations="disabled")
    result = _compare_images(actual, path)
    if result == "missing_baseline":
        if os.environ.get("GENERATE_VISUAL_BASELINES") == "1":
            actual.replace(path)
            print(f"Created baseline: {path}")
        else:
            actual.unlink(missing_ok=True)
            raise AssertionError(
                f"{state} {width}px: missing baseline screenshot {path.name}. "
                "Run with GENERATE_VISUAL_BASELINES=1 to create it intentionally."
            )
    elif result:
        actual.unlink(missing_ok=True)
        raise AssertionError(f"{state} {width}px: {result}")
    else:
        actual.unlink(missing_ok=True)


@pytest.mark.parametrize("width", VIEWPORTS)
def test_logged_out_auth_choice_visual(auth_visual_browser, width):
    context, page = _auth_page(auth_visual_browser, width)
    try:
        assert page.get_by_role("heading", name="Sign in required").is_visible()
        assert page.get_by_role("link", name="Continue with GitHub").is_visible()
        assert page.get_by_role("button", name="Continue with email").is_visible()
        _auth_snapshot(page, "logged_out", width)
    finally:
        context.close()


@pytest.mark.parametrize("width", VIEWPORTS)
def test_github_login_pending_visual_does_not_start_oauth(auth_visual_browser, width):
    context, page = _auth_page(auth_visual_browser, width)
    oauth_requests = []
    page.on(
        "request",
        lambda request: oauth_requests.append(request.url)
        if "/auth/login" in request.url
        else None,
    )
    try:
        login = page.get_by_role("link", name="Continue with GitHub")
        # Prevent navigation after the real click handler updates the pending UI.
        login.evaluate("el => el.addEventListener('click', event => event.preventDefault(), {once: true})")
        login.click()
        pending = page.locator(".login-prompt-actions a")
        assert pending.get_attribute("aria-busy") == "true"
        assert "Connecting to GitHub" in pending.inner_text()
        assert page.url.endswith("/my-projects")
        assert oauth_requests == [], f"unexpected OAuth request: {oauth_requests}"
        _auth_snapshot(page, "github_pending", width)
    finally:
        context.close()


@pytest.mark.parametrize("width", VIEWPORTS)
def test_email_link_pending_visual_disables_auth_controls(auth_visual_browser, width):
    context, page = _auth_page(auth_visual_browser, width)
    try:
        page.get_by_role("button", name="Continue with email").click()
        page.get_by_label("Email").fill("builder@example.com")
        page.evaluate(
            """() => {
                const nativeFetch = window.fetch.bind(window);
                window.__emailRequestStarted = false;
                window.fetch = (input, init) => {
                    if (String(input) === '/auth/email/start') {
                        window.__emailRequestStarted = true;
                        return new Promise(resolve => { window.__finishEmailRequest = resolve; });
                    }
                    return nativeFetch(input, init);
                };
            }"""
        )
        page.get_by_role("button", name="Email me a sign-in link").click()
        page.wait_for_function("window.__emailRequestStarted === true")
        send = page.get_by_role("button", name="Sending sign-in link")
        back = page.get_by_role("button", name="Back to sign-in options")
        assert send.is_disabled()
        assert send.get_attribute("aria-busy") == "true"
        assert back.is_disabled()
        _auth_snapshot(page, "email_pending", width)
    finally:
        context.close()


@pytest.mark.parametrize("width", VIEWPORTS)
def test_email_validation_error_visual(auth_visual_browser, width):
    context, page = _auth_page(auth_visual_browser, width)
    email_requests = []
    page.on(
        "request",
        lambda request: email_requests.append(request.url)
        if "/auth/email/start" in request.url
        else None,
    )
    try:
        page.get_by_role("button", name="Continue with email").click()
        page.get_by_label("Email").fill("not-an-email")
        page.get_by_role("button", name="Email me a sign-in link").click()
        error = page.get_by_role("alert")
        assert error.is_visible()
        assert "Enter a valid email address" in error.inner_text()
        assert page.get_by_label("Email").get_attribute("aria-invalid") == "true"
        assert email_requests == [], "invalid email must not reach the endpoint"
        _auth_snapshot(page, "email_validation_error", width)
    finally:
        context.close()


@pytest.mark.parametrize("width", VIEWPORTS)
def test_email_request_failure_visual_is_retryable(auth_visual_browser, width):
    context, page = _auth_page(auth_visual_browser, width)
    page.route(
        "**/auth/email/start",
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"mocked delivery failure"}',
        ),
    )
    try:
        page.get_by_role("button", name="Continue with email").click()
        page.get_by_label("Email").fill("builder@example.com")
        page.get_by_role("button", name="Email me a sign-in link").click()
        error = page.get_by_role("alert")
        assert error.is_visible()
        assert error.inner_text() == "We couldn't send the link. Check your connection and try again."
        assert page.get_by_role("button", name="Email me a sign-in link").is_enabled()
        _auth_snapshot(page, "email_request_failure", width)
    finally:
        context.close()


@pytest.mark.parametrize("width", VIEWPORTS)
def test_email_auth_error_recovers_after_a_retry(auth_visual_browser, width):
    context, page = _auth_page(auth_visual_browser, width)
    response_count = 0

    def email_response(route):
        nonlocal response_count
        response_count += 1
        if response_count == 1:
            route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"mocked delivery failure"}',
            )
        else:
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"ok":true,"sent":false}',
            )

    page.route("**/auth/email/start", email_response)
    try:
        page.get_by_role("button", name="Continue with email").click()
        email = page.get_by_label("Email")
        email.fill("builder@example.com")
        page.get_by_role("button", name="Email me a sign-in link").click()
        assert page.get_by_role("alert").is_visible()
        _auth_snapshot(page, "email_error_recovery", width)

        page.get_by_role("button", name="Email me a sign-in link").click()
        assert page.get_by_role("heading", name="Check your inbox").is_visible()
        assert response_count == 2
        _auth_snapshot(page, "email_recovered", width)
    finally:
        context.close()


@pytest.mark.parametrize("width", VIEWPORTS)
def test_existing_session_is_restored_after_reload(auth_visual_browser, width):
    context = auth_visual_browser.new_context(
        viewport={"width": width, "height": 900},
        reduced_motion="reduce",
    )
    context.add_cookies(
        [{"name": "critique_session", "value": "mock-session", "url": BASE_URL}]
    )
    page = context.new_page()
    seen_session_cookies = []

    def authenticated(route):
        seen_session_cookies.append(route.request.headers.get("cookie", ""))
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"authenticated":true}',
        )

    page.route("**/auth/check", authenticated)
    page.route(
        "**/api/projects/my/list",
        lambda route: route.fulfill(status=200, content_type="application/json", body="[]"),
    )
    try:
        page.goto(BASE_URL + "/my-projects", wait_until="networkidle")
        page.wait_for_function(
            "getComputedStyle(document.getElementById('logout-btn')).display !== 'none'"
        )
        assert page.locator("#login-btn").get_attribute("style") == "display: none;"
        assert page.locator("#logout-btn").get_attribute("style") == "display: inline;"
        assert page.get_by_role("heading", name="No projects yet").is_visible()
        page.reload(wait_until="networkidle")
        page.wait_for_function(
            "getComputedStyle(document.getElementById('logout-btn')).display !== 'none'"
        )
        assert page.locator("#login-btn").get_attribute("style") == "display: none;"
        assert page.locator("#logout-btn").get_attribute("style") == "display: inline;"
        assert len(seen_session_cookies) >= 2
        assert all("critique_session=mock-session" in value for value in seen_session_cookies)
        _auth_snapshot(page, "session_restored", width)
    finally:
        context.close()
