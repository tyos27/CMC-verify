import secrets
from datetime import datetime, timedelta, timezone
from store.links import db


def now_utc():
    return datetime.now(timezone.utc)


def make_code():
    return str(secrets.randbelow(900000) + 100000)


def cleanup():
    db.table("pending_game_verifies").delete().lt(
        "expires_at",
        now_utc().isoformat()
    ).execute()


def create_discord_pending(discord_id, discord_name, roblox_name):
    cleanup()

    db.table("pending_game_verifies").delete().eq(
        "discord_id",
        str(discord_id)
    ).execute()

    code = make_code()
    expires_at = now_utc() + timedelta(minutes=10)

    result = db.table("pending_game_verifies").insert({
        "discord_id": str(discord_id),
        "discord_name": str(discord_name),
        "roblox_id": None,
        "roblox_name": str(roblox_name).strip(),
        "roblox_display_name": None,
        "code": code,
        "expires_at": expires_at.isoformat()
    }).execute()

    print("created pending:", result.data)

    return code


def get_by_roblox_name(roblox_name):
    cleanup()

    name = str(roblox_name).strip()

    r = db.table("pending_game_verifies").select("*").ilike(
        "roblox_name",
        name
    ).execute()

    print("find pending by roblox_name:", name, r.data)

    if r.data:
        return r.data[0]

    return None


def attach_roblox_info(row_id, roblox_id, roblox_name, roblox_display_name=None):
    result = db.table("pending_game_verifies").update({
        "roblox_id": str(roblox_id),
        "roblox_name": str(roblox_name),
        "roblox_display_name": str(roblox_display_name) if roblox_display_name else str(roblox_name)
    }).eq(
        "id",
        row_id
    ).execute()

    print("attached roblox info:", result.data)


def consume_code(code):
    cleanup()

    clean = str(code).replace(" ", "").strip()

    r = db.table("pending_game_verifies").select("*").eq(
        "code",
        clean
    ).execute()

    print("consume code:", clean, r.data)

    if not r.data:
        return None

    row = r.data[0]

    db.table("pending_game_verifies").delete().eq(
        "id",
        row["id"]
    ).execute()

    return row
