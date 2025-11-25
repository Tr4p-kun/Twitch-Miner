# -*- coding: utf-8 -*-

import os
import requests
from dotenv import load_dotenv, set_key, find_dotenv

# ----------------- LOAD ENV -----------------
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# ----------------- ASK FOR AUTH CODE -----------------
auth_code = input("🔑 Enter your current Twitch Authorization Code: ").strip()
if not auth_code:
    print("❌ No authorization code entered! Exiting...")
    exit(1)

set_key(dotenv_path, "AUTH_CODE", auth_code)

# ----------------- REQUEST REFRESH TOKEN -----------------
url = "https://id.twitch.tv/oauth2/token"
data = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": auth_code,
    "grant_type": "authorization_code",
    "redirect_uri": "http://localhost:3000"
}

print("🔥 Exchanging authorization code for refresh token...")
response = requests.post(url, data=data)

if response.status_code == 200:
    json_data = response.json()
    refresh_token = json_data["refresh_token"]
    print("\n✅ SUCCESS! Refresh token obtained:")
    print(f"{refresh_token}")

    set_key(dotenv_path, "TWITCH_REFRESH_TOKEN", refresh_token)
    print("\n➡️ Refresh token automatically written to .env!")
else:
    print(f"❌ ERROR: {response.status_code}")
    print(response.text)
