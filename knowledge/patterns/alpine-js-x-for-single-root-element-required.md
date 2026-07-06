---
title: Alpine.js x-for: single root element required
category: patterns
tags: [alpine.js, x-for, template, html, frontend]
created: 2026-07-06
---

# Alpine.js x-for: single root element required

## Problem
x-for iterates over a template — it requires exactly ONE root element inside the template block. A second sibling element is silently dropped (no error, just missing from the DOM).

## Wrong
```html
<template x-for="item in items">
  <div x-text="item.name"></div>
  <span x-text="item.value"></span>  <!-- silently dropped -->
</template>
```

## Fix — wrap with display:contents
```html
<template x-for="item in items">
  <div style="display:contents">
    <div x-text="item.name"></div>
    <span x-text="item.value"></span>
  </div>
</template>
```

display:contents makes the wrapper invisible to the layout engine (no extra box), so flex/grid parents behave as if the children are direct.

## Why it happens
Alpine clones the template's firstElementChild on each iteration — there is no error for extra siblings, they just never get touched.
