---
title: Alpine.js x-show vs x-if: DOM presence and Playwright implications
category: patterns
tags: [alpine.js, x-show, x-if, playwright, visibility, DOM]
created: 2026-07-06
---

# Alpine.js x-show vs x-if: DOM presence and Playwright implications

## Difference
- x-show: element is always in the DOM, toggled with display:none. Playwright can locate it but interactions fail if hidden.
- x-if: element is removed from DOM entirely when false. Playwright locators throw if element doesn't exist yet.

## Playwright gotcha — button text doesn't change with x-show
```html
<!-- Common Alpine loading pattern -->
<button @click="runReport()">
  <span x-show="!loading">Run Report</span>
  <span x-show="loading">Loading...</span>
</button>
```
```python
# WRONG — button always has text 'Run Report' AND 'Loading...' in innerHTML
# (both spans exist; only one is display:none)
page.wait_for_selector("button:has-text('Run Report'):not(:has-text('Loading'))")  # never resolves

# RIGHT — wait for the API response that the button triggers
with page.expect_response(lambda r: '/api/report-builder/reports/' in r.url) as resp:
    page.click("button:has-text('Run Report')")
response = resp.value
```

## When to use x-if vs x-show
- x-if: conditional sections that are expensive to render or depend on data that may not exist yet (avoids prop-drilling errors on undefined)
- x-show: toggles where the element needs to animate, or flips frequently (cheaper than DOM insert/remove)
