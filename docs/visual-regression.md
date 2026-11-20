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

Baselines are not created automatically. Run the suite with
`GENERATE_VISUAL_BASELINES=1` to create missing baseline files, then review
each new image before committing.

## Update baselines after intentional UI changes

Regenerate only the affected baselines with `GENERATE_VISUAL_BASELINES=1`,
review the diff carefully, and commit the updated PNGs. Do not blindly
regenerate all baselines.

## Run a single test

```bash
python -m pytest tests/test_visual_regression.py::test_homepage_screenshot_regression -q
```

## Responsive assertions

The tests assert no horizontal overflow at 375, 496, 511, 768, 1024, 1280, and 1440px.

## CI artifacts

On failure, actual screenshots are uploaded as `playwright-report` artifacts.
