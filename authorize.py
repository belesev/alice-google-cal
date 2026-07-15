"""
Run this script ONCE locally to get your OAuth2 refresh token.

Prerequisites:
  1. Go to https://console.cloud.google.com/
  2. Create a project, enable "Google Calendar API"
  3. Create OAuth 2.0 credentials (Desktop app type)
  4. Download the credentials JSON and save it as credentials.json next to this script
  5. Run: python authorize.py

After running, copy the printed values into Yandex Cloud Function environment variables:
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  GOOGLE_REFRESH_TOKEN
  CALENDAR_TIMEZONE  (optional, default: Europe/Moscow)
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar.events.owned']

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

print("\n=== Add these to Yandex Cloud Function environment variables ===\n")
print(f"GOOGLE_CLIENT_ID={creds.client_id}")
print(f"GOOGLE_CLIENT_SECRET={creds.client_secret}")
print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
print("\nOptional (default: Europe/Moscow):")
print("CALENDAR_TIMEZONE=Europe/Moscow")
