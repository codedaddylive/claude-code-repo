---
title: Alpine.js x-model scoping: always target specific elements
category: patterns
tags: [alpine.js, x-model, selector, playwright, debugging]
created: 2026-07-06
---

# Alpine.js x-model scoping: always target specific elements

## Problem
Generic selectors like `page.select_option('select', value)` resolve to the FIRST matching element in the DOM. Alpine.js SPAs often have many `<select>` elements on a single page (filters, dropdowns, report forms). The first one may be hidden or in a different section — the action silently targets the wrong element or times out.

## Rule
Always scope selectors to the x-model attribute binding or a stable ancestor:
```python
# Wrong — matches first of 8 selects, which may be hidden
page.select_option('select', '9')

# Right — targets the exact Alpine binding
page.select_option("select[x-model='rb.reportForm.team_id']", '9')
```

## Same applies to inputs, buttons, checkboxes
```python
# Prefer x-ref or name attribute scoping
page.fill("input[x-ref='rbImportFile']", path)
page.click("button[x-on:click='rb.runReport()']")
```

## Also applies to Playwright locators
```python
# Scope to a container first
form = page.locator('#rb-report-form')
form.select_option("select[x-model='team_id']", '7')
```
