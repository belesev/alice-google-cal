# Plan: Account Linking for Public Skill

## Problem

The current skill stores one hardcoded Google refresh token in Yandex Cloud Function
environment variables. This means every user of the public skill writes events to
**the same Google Calendar** — the owner's. Each user must instead authorize their
own Google account.

## Solution Overview

Alice supports OAuth 2.0 account linking. When enabled, Alice redirects the user
to an authorization page, receives a token, stores it, and passes it to the skill
on every subsequent request via `event["session"]["user"]["access_token"]`.

Because Google exposes standard OAuth 2.0 endpoints, no custom authorization server
is needed. Alice can talk to Google directly.

---

## How the Flow Works (After the Change)

```
User invokes skill
      │
      ▼
Alice checks: is account linked?
      │
      ├─ NO ──► Alice shows "Link account" card
      │              │
      │              ▼
      │         User taps → Alice redirects to Google consent screen
      │              │
      │              ▼
      │         User grants "Google Calendar" permission
      │              │
      │              ▼
      │         Google redirects to https://social.yandex.net/broker/redirect
      │         with authorization code
      │              │
      │              ▼
      │         Alice exchanges code → access_token + refresh_token
      │         (Alice stores both; refreshes automatically on expiry)
      │
      └─ YES ──► event["session"]["user"]["access_token"] contains
                 a valid Google access token
                      │
                      ▼
                 skill calls Google Calendar API with Bearer token
```

---

## Step-by-Step Implementation

### Step 1 — Google Cloud Console

1. Open the existing OAuth 2.0 Client ID (Desktop type, used by `authorize.py`).
   **Change the application type from "Desktop" to "Web application"** — desktop
   clients cannot use arbitrary redirect URIs.
2. Under **Authorized redirect URIs**, add:
   ```
   https://social.yandex.net/broker/redirect
   ```
3. Save. Download the updated `credentials.json` (keep it out of git).

### Step 2 — Yandex Dialogs Console

In the skill settings, open the **Account Linking** section and fill in:

| Field | Value |
|-------|-------|
| Authorization URL | `https://accounts.google.com/o/oauth2/v2/auth?scope=https://www.googleapis.com/auth/calendar.events.owned&access_type=offline&prompt=consent` |
| Token URL | `https://oauth2.googleapis.com/token` |
| Client ID | your Google OAuth2 client ID |
| Client Secret | your Google OAuth2 client secret |

The `prompt=consent` parameter forces Google to return a refresh token on every
authorization, not just the first time. Alice needs the refresh token to silently
renew the access token when it expires (after 1 hour).

### Step 3 — Update `main.py`

**Remove** three environment variables: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
`GOOGLE_REFRESH_TOKEN`. They are no longer needed at runtime.

**Read the token from the request** instead:

```python
# At the top of handler():
access_token = event.get('session', {}).get('user', {}).get('access_token')
if not access_token:
    return {
        'version': event['version'],
        'session': event['session'],
        'response': {
            'text': 'Чтобы добавлять события, привяжи аккаунт Google. '
                    'Нажми кнопку «Привязать аккаунт» в приложении Яндекс.',
            'end_session': True,
            'card': {
                'type': 'BigImage',
                'image_id': ...,   # optional: store artwork image in Yandex Dialogs
            },
        },
        'start_account_linking': {},   # triggers the linking card in Alice apps
    }
```

**Simplify `_create_event`** — no token refresh logic, just pass the token:

```python
def _create_event(title, start_dt, end_dt, description, access_token):
    body = json.dumps({...}).encode()
    url = f'https://www.googleapis.com/calendar/v3/calendars/primary/events'
    req = urllib.request.Request(url, data=body, headers={
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    })
    urllib.request.urlopen(req)
```

Remove `_get_access_token()` entirely.

**Pass `access_token` through `_finish`** down to `_create_event`.

### Step 4 — Remove Env Vars from Yandex Cloud Function

Delete `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` from
the function's environment variables in Yandex Cloud console.
`CALENDAR_TIMEZONE` can stay (it's a user preference, not a secret).

### Step 5 — Update `authorize.py`

`authorize.py` is no longer needed for production setup. It can be kept as a
developer utility for local testing, or removed. Add a note explaining it is
obsolete.

---

## What Alice Handles Automatically

- Token storage (per user, per device)
- Access token refresh using the stored refresh token
- Re-authorization prompt if the refresh token is revoked

## Security Considerations

- The access token in `event["session"]["user"]["access_token"]` is scoped to
  `calendar.events.owned` only — it cannot read contacts, drive, or other Google data.
- Tokens are stored by Yandex, not by this skill. The skill never persists tokens.
- If a user revokes access in their [Google Account settings](https://myaccount.google.com/permissions),
  the next request will have no token and the skill will prompt re-linking.

---

## Files Changed

| File | Change |
|------|--------|
| `main.py` | Remove `_get_access_token()`, read token from request, add no-token guard |
| `authorize.py` | Mark as obsolete or remove |
| `requirements.txt` | No change (already stdlib-only) |
| `ACCOUNT_LINKING_PLAN.md` | This document |

## Files Not Changed

| File | Reason |
|------|--------|
| `testdata/*.json` | Need new test files with `access_token` in `session.user` |

A new set of test payloads should be created where `session.user.access_token`
contains a dummy Bearer token, to verify the happy path without real Google calls.

---

## References

- [Alice: When to use account linking](https://yandex.ru/dev/dialogs/alice/doc/ru/auth/when-to-use)
- [How authorization works — Yandex Smart Home](https://yandex.ru/dev/dialogs/smart-home/doc/en/auth/how-it-works)
- [Google OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
