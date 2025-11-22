# -*- coding: utf-8 -*-

from dotenv import load_dotenv
import os, sys, time, random, threading, requests, logging
from pathlib import Path
import json

# ---------- STRICT .ENV LOADER ----------

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
        else:
            return value
    except Exception as e:
        print(f"❌ Failed to parse .env variable '{name}' ({value}) as {var_type.__name__}: {e}")
        sys.exit(1)

# Load variables
CLIENT_ID           = load_env_var("CLIENT_ID")
CLIENT_SECRET       = load_env_var("CLIENT_SECRET")
REFRESH_TOKEN       = load_env_var("TWITCH_REFRESH_TOKEN")
USERNAME            = load_env_var("USERNAME")
GAME_ID             = load_env_var("GAME_ID")
DROPS_ONLY_MODE     = load_env_var("DROPS_ONLY_MODE", bool)
MINING_DURATION_MIN = load_env_var("MINING_DURATION_MIN", int)
MINING_DURATION_MAX = load_env_var("MINING_DURATION_MAX", int)
VIEWER_THRESHOLD    = load_env_var("VIEWER_THRESHOLD", int)
CHECK_INTERVAL      = load_env_var("CHECK_INTERVAL", int)
DEBUG               = load_env_var("DEBUG", bool)


# ---------- PRINT HELPERS ----------
def log_debug(*args, **kwargs):
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)


def log_info(*args, **kwargs):
    # current "silent mode" logic
    txt = " ".join(map(str, args))
    if DEBUG or txt.startswith(("🚀", "✅", "🎮", "⏸️", "🎲", "[START]", "[END]", "  ⏳")) \
            or "Open https://www.twitch.tv/activate" in txt \
            or "and enter this code:" in txt:
        print(*args, **kwargs)


# ---------- LIB ----------
_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, StreamerSettings

# ---------- KILL NOISE ----------
for lib in [
    'charset_normalizer', 'urllib3', 'requests', 'Twitch', 'WebSocketsPool',
    'TwitchWebSocket', 'irc', 'TwitchChannelPointsMiner'
]:
    logging.getLogger(lib).setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.CRITICAL)


# ---------- HELPERS ----------
def get_token(client_id, client_secret, refresh_token):
    r = requests.post(
        "https://id.twitch.tv/oauth2/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        },
        timeout=5
    )
    if r.status_code != 200:
        log_info("❌ Token error", r.text)
        sys.exit(1)
    token = r.json()["access_token"]
    log_debug("Token fetched:", token)
    return token


def get_game_id_by_name(game_name, token, client_id, client_secret):
    headers = {"Authorization": f"Bearer {token}", "Client-Id": client_id}
    params = {"name": game_name}
    r = requests.get("https://api.twitch.tv/helix/games", headers=headers, params=params, timeout=5)

    if r.status_code == 401:
        log_debug("Token expired, refreshing...")
        token = get_token(client_id, client_secret, REFRESH_TOKEN)
        headers["Authorization"] = f"Bearer {token}"
        r = requests.get("https://api.twitch.tv/helix/games", headers=headers, params=params, timeout=5)

    log_debug("Get Game Response:", json.dumps(r.json(), indent=2))
    if r.status_code == 200 and r.json()["data"]:
        return r.json()["data"][0]["id"]
    return None


def get_drops_streams(game_id, token, client_id, client_secret, refresh_token):
    drops, cursor = [], None
    headers = {"Authorization": f"Bearer {token}", "Client-Id": client_id}
    params = {"game_id": game_id, "first": 100, "type": "live"}

    for _ in range(2):
        while True:
            if cursor:
                params["after"] = cursor

            try:
                r = requests.get("https://api.twitch.tv/helix/streams",
                                 headers=headers, params=params, timeout=5)

                if r.status_code == 401:
                    log_debug("Token expired during stream fetch, refreshing...")
                    token = get_token(client_id, client_secret, refresh_token)
                    headers["Authorization"] = f"Bearer {token}"
                    break

                if r.status_code != 200:
                    log_debug("Non-200 response:", r.status_code, r.text)
                    break

                data = r.json()
                log_debug("Fetched streams:", json.dumps(data, indent=2))

                for s in data["data"]:
                    if s["viewer_count"] >= VIEWER_THRESHOLD \
                            and (not DROPS_ONLY_MODE or "DropsEnabled" in s.get("tags", [])):
                        drops.append(s["user_login"])

                cursor = data.get("pagination", {}).get("cursor")
                if not cursor:
                    break
                time.sleep(0.5)

            except Exception as e:
                log_debug("Exception in get_drops_streams:", e)
                break

        if drops:
            break

    log_debug("Drops pool:", drops)
    return drops


# ---------- BACKGROUND MINUTE COUNTER ----------
def minute_counter(total_minutes: int):
    for left in range(total_minutes - 1, 0, -1):
        time.sleep(60)
        log_info(f"  ⏳  {left} min left", flush=True)


# ---------- SINGLE MINER ----------
def mine_single(streamer, token, client_id, client_secret, refresh_token):
    log_info(f"[START] {streamer}")

    streamer_obj = Streamer(
        username=streamer,
        settings=StreamerSettings(
            claim_drops=True, watch_streak=True,
            make_predictions=False, follow_raid=False,
            chat=False, claim_moments=False, community_goals=False
        )
    )

    threading.Thread(
        target=TwitchChannelPointsMiner(
            username=USERNAME,
            password="",
            claim_drops_startup=True,
            disable_ssl_cert_verification=False
        ).mine,
        args=([streamer_obj],),
        daemon=True
    ).start()

    minutes = random.randint(MINING_DURATION_MIN, MINING_DURATION_MAX)
    log_info(f"  ⏳  {minutes} min …")
    threading.Thread(target=minute_counter, args=(minutes,), daemon=True).start()
    time.sleep(minutes * 60)
    log_info(f"[END] {streamer}")

    return streamer in get_drops_streams(GAME_ID, token, client_id, client_secret, refresh_token)


# ---------- MAIN ----------
if __name__ == "__main__":
    log_info("🚀  Miner started")
    token = get_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
    log_info("✅  Token OK")

    if input("\n🎮  Change game? (yes/no): ").strip().lower() in {"yes", "y"}:
        name = input(">>  Game name: ").strip()
        if name:
            gid = get_game_id_by_name(name, token, CLIENT_ID, CLIENT_SECRET)
            if gid:
                GAME_ID = gid
                log_info(f"✅  Game-ID {gid} set!")

    log_info("  Starting in 3 s …")
    time.sleep(3)

    while True:
        drops = get_drops_streams(GAME_ID, token, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
        if not drops:
            log_info(f"⏸️   Idle – none found, waiting {CHECK_INTERVAL} sec …")
            time.sleep(CHECK_INTERVAL)
            continue

        streamer = random.choice(drops)
        log_info(f"🎲  {streamer}  (pool: {len(drops)})")

        still = mine_single(streamer, token, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
        log_info(f"✅  Switch  ({'live' if still else 'offline'})  – 30 s")
        time.sleep(30)
