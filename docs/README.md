# Alice → Google Calendar skill


A [Yandex Alice](https://yandex.ru/dev/dialogs/alice/) skill that adds events to Google Calendar via voice. Deployed as a Yandex Cloud Function.

## How it works

The skill runs a 3-step dialog (all in Russian):

| Turn | Alice asks | User says |
|------|-----------|-----------|
| 1 | "Скажи название события" | e.g. *"Встреча с командой"* |
| 2 | "На какую дату?" | e.g. *"двадцать пятое мая"* or *"завтра"* |
| 3 | "В котором часу?" | e.g. *"в три часа дня"* |

If the user names date and time in a single phrase at step 2, step 3 is skipped.  
Saying *"отмена"*, *"выход"*, *"стоп"* at any point cancels the flow.

Created events have a `[from Alice]` title prefix and a description with debug metadata (session ID, user ID, original utterances).

## Project structure

```
main.py          # Yandex Cloud Function handler
authorize.py     # One-time local script to obtain OAuth2 refresh token
requirements.txt # No runtime dependencies (stdlib urllib only)
testdata/        # Sample Alice request payloads for manual testing
.gitignore
```

## Setup

### 1. Google Cloud — enable Calendar API and create credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable **Google Calendar API** for the project.
3. Create an **OAuth 2.0 Client ID** (application type: *Desktop app*).
4. Download the JSON file and save it as `credentials.json` in this directory.

> `credentials.json` is listed in `.gitignore` — never commit it.

### 2. Get a refresh token

```bash
pip install google-auth-oauthlib
python authorize.py
```

A browser window will open for Google sign-in. After authorizing, the script prints three values:

```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...
```

### 3. Deploy to Yandex Cloud Functions

```bash
zip main.zip main.py
```

Create a function (runtime: **Python 3.12**) and upload `main.zip`.

Set the entry point to `main.handler`.

Add the following environment variables:

| Variable | Value |
|----------|-------|
| `GOOGLE_CLIENT_ID` | from step 2 |
| `GOOGLE_CLIENT_SECRET` | from step 2 |
| `GOOGLE_REFRESH_TOKEN` | from step 2 |
| `CALENDAR_TIMEZONE` | e.g. `Europe/Moscow` (default) |

### 4. Register the skill in Yandex Dialogs

Point the webhook URL at your deployed Cloud Function.

## Testing

The `testdata/` directory contains ready-made Alice request payloads you can paste into the Yandex Dialogs testing console or send via `curl`:

| File | Simulates |
|------|-----------|
| `01_new_session.json` | User opens the skill |
| `02_title.json` | User says the event title |
| `03_date.json` | User says only the date |
| `03_date_and_time.json` | User says date and time in one phrase |
| `04_time.json` | User says the time (follows `03_date.json`) |

```bash
curl -X POST <your-function-url> \
  -H "Content-Type: application/json" \
  -d @testdata/01_new_session.json
```
