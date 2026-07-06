---
title: Playwright: wait for API response, not DOM load state, in Alpine.js apps
category: patterns
tags: [playwright, alpine.js, async, wait, api, timing, reliability]
created: 2026-07-06
---

# Playwright: wait for API response, not DOM load state, in Alpine.js apps

## Problem
Alpine.js fetches data after page load. DOM elements (cards, tables, headings) exist in the HTML from the start — they are just hidden or empty. Waiting for an element to 'appear' succeeds immediately (it was already there), but the data hasn't arrived yet. Subsequent interactions then fail on empty/stale state.

## Wrong
```python
page.click("button:has-text('Run Report')")
page.wait_for_selector('h3:has-text("Total Hours per User")')  # already in DOM, resolves instantly
data = page.locator('.result-table').inner_text()  # empty — fetch not done yet
```

## Right — intercept the API call
```python
with page.expect_response(
    lambda r: '/api/report-builder/reports/' in r.url and r.status == 200
) as resp_info:
    page.click("button:has-text('Run Report')")

response = resp_info.value
assert response.status == 200

# Now the DOM reflects the response
data = page.locator('.result-table').inner_text()
```

## For long-running requests (>30s default timeout)
```python
with page.expect_response(
    lambda r: '/api/report-builder/reports/' in r.url,
    timeout=120_000  # 2 min for large teams
) as resp_info:
    page.click("button:has-text('Run Report')")
```

## Also applies to scroll-into-view
Calling scroll_into_view_if_needed on an element that exists but is hidden (x-show=false) will time out. Always wait for the API response before scrolling to result elements.
