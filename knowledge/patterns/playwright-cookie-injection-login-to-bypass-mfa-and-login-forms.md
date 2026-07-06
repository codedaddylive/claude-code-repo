---
title: Playwright: cookie injection login to bypass MFA and login forms
category: patterns
tags: [playwright, auth, mfa, cookie, fastapi, testing, login]
created: 2026-07-06
---

# Playwright: cookie injection login to bypass MFA and login forms

## Problem
Navigating login forms in Playwright is fragile — MFA dialogs, Okta redirects, and overlay modals block form-based login. For internal apps with a test user (no MFA), inject the session cookie directly via API.

## Pattern (FastAPI + httpOnly cookie auth)
```python
import requests, urllib3
urllib3.disable_warnings()

BASE_URL = 'https://localhost:5173'

def get_session_cookie():
    r = requests.post(
        f'{BASE_URL}/api/auth/login',
        json={'username': 'testuser', 'password': 'QATest1234!'},
        verify=False
    )
    r.raise_for_status()
    return r.cookies.get('qa_session')

@pytest.fixture
def authed_page(page):
    token = get_session_cookie()
    page.context.add_cookies([{
        'name': 'qa_session',
        'value': token,
        'domain': 'localhost',
        'path': '/',
        'httpOnly': True,
        'secure': True,
    }])
    page.goto(f'{BASE_URL}/')
    page.wait_for_load_state('networkidle')
    return page
```

## Rules
- Call add_cookies BEFORE page.goto — cookies set after navigation don't apply to that load
- Use requests (not Playwright) for the login call — simpler, no browser overhead
- verify=False is required for self-signed certs on internal servers
- Never use the admin user in automation — MFA is enabled, it will block
