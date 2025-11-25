# -*- coding: utf-8 -*-
import os
import sys
import time
import random
import threading
import requests
import logging
import json
from pathlib import Path
from dotenv import load_dotenv

# --- AUTH FIX FOR LOGIN CODE VISIBILITY ---
login_logger = logging.getLogger("TwitchChannelPointsMiner.classes.TwitchLogin")
login_logger.setLevel(logging.DEBUG)
# ------------------------------------------

# ---------- 1. CONFIG & ENV ----------
load_dotenv()


def load_env_var(name, var_type=str, required=True):
    value = os.getenv(name)
    if required and (value is None or value.strip() == ""):
        print(f"❌ Required .env variable '{name}' is missing!")
        sys.exit(1)
    try:
        if var_type == bool:
            return value.lower() == "true"
        elif var_type == int:
            return int(value)
        return value
    except Exception as e:
        print(f"❌ Error parsing '{name}': {e}")
        sys.exit(1)


CLIENT_ID = load_env_var("CLIENT_ID")
CLIENT_SECRET = load_env_var("CLIENT_SECRET")
REFRESH_TOKEN = load_env_var("TWITCH_REFRESH_TOKEN")
USERNAME = load_env_var("USERNAME")
GAME_ID = load_env_var("GAME_ID")
DROPS_ONLY_MODE = load_env_var("DROPS_ONLY_MODE", bool)
MINING_DURATION_MIN = load_env_var("MINING_DURATION_MIN", int)
MINING_DURATION_MAX = load_env_var("MINING_DURATION_MAX", int)
VIEWER_THRESHOLD = load_env_var("VIEWER_THRESHOLD", int)
CHECK_INTERVAL = load_env_var("CHECK_INTERVAL", int)
DEBUG = load_env_var("DEBUG", bool)

# ---------- 2. LOGGING SETUP (DYNAMIC) ----------

FULL_FORMATTER = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s', datefmt="%H:%M:%S")
SIMPLE_FORMATTER = logging.Formatter('%(message)s')

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

root_logger = logging.getLogger()
root_logger.addHandler(console_handler)

lib_logger = logging.getLogger("TwitchChannelPointsMiner")

if DEBUG:
    console_handler.setFormatter(FULL_FORMATTER)
    root_logger.setLevel(logging.INFO)
    lib_logger.setLevel(logging.DEBUG)
    print("🔧 DEBUG MODE: ON - Detailed library logs enabled.")
else:
    console_handler.setFormatter(SIMPLE_FORMATTER)
    root_logger.setLevel(logging.INFO)
    lib_logger.setLevel(logging.WARNING)


logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("charset_normalizer").setLevel(logging.WARNING)

def log_info(*args):
    logging.info(" ".join(map(str, args)))

def log_debug(*args):
    if DEBUG:
        logging.debug(" ".join(map(str, args)))

# ---------- 3. IMPORTS ----------
_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))

try:
    from TwitchChannelPointsMiner import TwitchChannelPointsMiner
    from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, StreamerSettings
except ImportError as e:
    log_info("❌ Could not import TwitchChannelPointsMiner. Check path!")
    sys.exit(1)


# ---------- 4. API HELPERS ----------
def get_token(client_id, client_secret, refresh_token):
    try:
        r = requests.post(
            "https://id.twitch.tv/oauth2/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            },
            timeout=10
        )
        r.raise_for_status()
        return r.json()["access_token"]
    except Exception as e:
        log_info(f"❌ Token error: {e}")
        sys.exit(1)


def get_game_id_by_name(game_name, token, client_id, client_secret):
    headers = {"Authorization": f"Bearer {token}", "Client-Id": client_id}
    params = {"name": game_name}
    try:
        r = requests.get("https://api.twitch.tv/helix/games", headers=headers, params=params, timeout=10)
        if r.status_code == 401:
            log_debug("Token expired, refreshing...")
            token = get_token(client_id, client_secret, REFRESH_TOKEN)
            headers["Authorization"] = f"Bearer {token}"
            r = requests.get("https://api.twitch.tv/helix/games", headers=headers, params=params, timeout=10)

        if r.status_code == 200 and r.json()["data"]:
            return r.json()["data"][0]["id"]
    except Exception as e:
        log_debug(f"Error fetching game ID: {e}")
    return None


def get_drops_streams(game_id, token, client_id, client_secret, refresh_token):
    drops, cursor = [], None
    headers = {"Authorization": f"Bearer {token}", "Client-Id": client_id}
    params = {"game_id": game_id, "first": 100, "type": "live"}

    for _ in range(2):
        if cursor:
            params["after"] = cursor

        try:
            r = requests.get("https://api.twitch.tv/helix/streams", headers=headers, params=params, timeout=10)

            if r.status_code == 401:
                token = get_token(client_id, client_secret, refresh_token)
                headers["Authorization"] = f"Bearer {token}"
                continue

            if r.status_code != 200:
                break

            data = r.json()
            for s in data.get("data", []):
                if s["viewer_count"] >= VIEWER_THRESHOLD and \
                        (not DROPS_ONLY_MODE or "DropsEnabled" in s.get("tags", [])):
                    drops.append(s["user_login"])

            cursor = data.get("pagination", {}).get("cursor")
            if not cursor:
                break

        except Exception:
            break

    return drops


# ---------- 5. MINING LOGIC ----------
def minute_counter(total_minutes: int):
    for left in range(total_minutes - 1, 0, -1):
        time.sleep(60)
        print(f"  ⏳  {left} min left", flush=True)


def mine_single(streamer, token, client_id, client_secret, refresh_token):
    log_info(f"[START] {streamer}")

    streamer_obj = Streamer(
        username=streamer,
        settings=StreamerSettings(
            claim_drops=True, watch_streak=True,
            make_predictions=False, follow_raid=False, chat=False
        )
    )

    miner = TwitchChannelPointsMiner(
        username=USERNAME,
        password="",
        claim_drops_startup=True,
    )

    t = threading.Thread(
        target=miner.mine,
        args=([streamer_obj],),
        daemon=True
    )
    t.start()

    minutes = random.randint(MINING_DURATION_MIN, MINING_DURATION_MAX)
    print(f"  ⏳  {minutes} min mining duration set", flush=True)

    threading.Thread(target=minute_counter, args=(minutes,), daemon=True).start()

    time.sleep(minutes * 60)

    log_info(f"[END] {streamer}")

    live_pool = get_drops_streams(GAME_ID, token, client_id, client_secret, refresh_token)
    return streamer in live_pool


# ---------- 6. MAIN ----------
if __name__ == "__main__":
    if sys.platform == "win32":
        os.system('color')

    log_info("🚀  Miner started")

    token = get_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
    log_info("✅  Token OK")

    try:
        sys.stdout.flush()
        choice = input("\n🎮  Change game? (yes/no): ").strip().lower()
        if choice in {"yes", "y"}:
            name = input(">>  Game name: ").strip()
            if name:
                gid = get_game_id_by_name(name, token, CLIENT_ID, CLIENT_SECRET)
                if gid:
                    GAME_ID = gid
                    log_info(f"✅  Game-ID {gid} set!")
                else:
                    log_info("❌  Game not found, keeping default.")
    except Exception:
        pass

    log_info("  Starting in 3 s …")
    time.sleep(3)

    while True:
        drops = get_drops_streams(GAME_ID, token, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)

        if not drops:
            log_info(f"⏸️   Idle – none found, waiting {CHECK_INTERVAL} sec …")
            time.sleep(CHECK_INTERVAL)
            continue

        streamer = random.choice(drops)
        log_info(f"🎲  Selected: {streamer} (Pool size: {len(drops)})")

        still_live = mine_single(streamer, token, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)

        log_info(f"✅  Switching... (Previous was {'live' if still_live else 'offline'}) – Waiting 30s")
        time.sleep(30)