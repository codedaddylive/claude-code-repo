---
title: Playwright: three-viewport screenshot verification for web UIs
category: patterns
tags: [playwright, screenshot, responsive, viewport, testing, verification]
created: 2026-07-06
---

# Playwright: three-viewport screenshot verification for web UIs

## Standard viewports
Always capture at three widths when verifying UI changes — mobile, tablet, desktop:
```python
VIEWPORTS = [
    {'name': 'mobile',  'width': 375,  'height': 812},
    {'name': 'tablet',  'width': 768,  'height': 1024},
    {'name': 'desktop', 'width': 1440, 'height': 900},
]

for vp in VIEWPORTS:
    page.set_viewport_size({'width': vp['width'], 'height': vp['height']})
    page.screenshot(path=f'/tmp/{project}_{feature}_{vp["name"]}.png')
```

## Read screenshots back with the Read tool
After saving, display them inline:
```
Read('/tmp/qa_portal_report_builder_desktop.png')
```

## Coordinate scale factor
On some Linux setups the screenshot pixel dimensions exceed the viewport (e.g. 1627px wide for a 1440px viewport — scale factor ~1.13). This affects coordinate-based clicks. Prefer locator-based interactions over coordinate clicks to avoid this.

## Meaningful wait before screenshot
Don't screenshot immediately after navigation — wait for data:
```python
page.goto(url)
page.wait_for_load_state('networkidle')
# or wait for a specific element that proves data loaded:
page.wait_for_selector('.result-table:not(:empty)', timeout=30_000)
page.screenshot(path='...')
```
