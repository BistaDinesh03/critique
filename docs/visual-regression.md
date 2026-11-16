# Visual Regression Testing

Critique uses Playwright (Python) with Chromium for visual regression tests.

## Run locally

```bash
cd backend
pip install -r requirements.txt
python -m playwright install chromium
python -m pytest tests/test_visual_regression.py -q
```

## Generate initial baselines

Baselines are created automatically on first run when missing. Review them before committing.

## Update baselines after intentional UI changes

Delete the affected baseline file and re-run the test to regenerate. Review the diff carefully before committing.

## Run a single test

```bash
python -m pytest tests/test_visual_regression.py::test_homepage_screenshot_regression -q
```

## Responsive assertions

The tests assert no horizontal overflow at 375, 496, 511, 768, 1024, 1280, and 1440px.

## CI artifacts

On failure, actual screenshots are uploaded as `playwright-report` artifacts.
