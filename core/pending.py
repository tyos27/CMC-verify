import base64
import hashlib
import hmac
import json
import secrets
import time

from core.env import Env


TTL_SECONDS = 600


def b64e(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def b64d(data):
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode())


def secret_key():
    raw = f"{Env.game_api_key}:{Env.roblox_client_secret}"
    return raw.encode()


def sign(body):
    digest = hmac.new(
        secret_key(),
        body.encode(),
        hashlib.sha256
    ).digest()

    return b64e(digest)


def make_state(discord_id, channel_id=None, message_id=None, discord_name=None):
    payload = {
        "d": str(discord_id),
        "c": str(channel_id) if channel_id is not None else "",
        "m": str(message_id) if message_id is not None else "",
        "n": str(discord_name) if discord_name is not None else "",
        "e": int(time.time()) + TTL_SECONDS,
        "x": secrets.token_urlsafe(8)
    }

    body = b64e(
        json.dumps(
            payload,
            separators=(",", ":"),
            ensure_ascii=False
        ).encode()
    )

    token = body + "." + sign(body)

    print("oauth state made:", token, discord_id)

    return token


def take(state):
    try:
        raw = str(state or "")

        if "." not in raw:
            print("oauth state invalid: no separator")
            return None

        body, sig = raw.rsplit(".", 1)

        expected = sign(body)

        if not hmac.compare_digest(sig, expected):
            print("oauth state invalid: bad signature")
            return None

        payload = json.loads(b64d(body).decode())

        if int(payload.get("e", 0)) < int(time.time()):
            print("oauth state invalid: expired")
            return None

        result = {
            "discord_id": payload.get("d"),
            "channel_id": payload.get("c") or None,
            "message_id": payload.get("m") or None,
            "discord_name": payload.get("n") or None
        }

        print("oauth state take ok:", result)

        return result

    except Exception as e:
        print("oauth state take failed:", e)
        return None


def hold(state, discord_id, channel_id, message_id, discord_name=None):
    print("oauth state hold ignored: stateless mode")


def put(state, discord_id, channel_id, message_id, discord_name=None):
    print("oauth state put ignored: stateless mode")
