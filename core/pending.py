from datetime import datetime, timedelta, timezone
from store.links import db


def now_utc():
    return datetime.now(timezone.utc)


def cleanup():
    try:
        db.table("oauth_states").delete().lt(
            "expires_at",
            now_utc().isoformat()
        ).execute()
    except Exception as e:
        print("oauth state cleanup failed:", e)


def hold(state, discord_id, channel_id, message_id, discord_name=None):
    cleanup()

    expires_at = now_utc() + timedelta(minutes=10)

    row = {
        "state": str(state),
        "discord_id": str(discord_id),
        "channel_id": str(channel_id) if channel_id is not None else None,
        "message_id": str(message_id) if message_id is not None else None,
        "discord_name": str(discord_name) if discord_name is not None else None,
        "expires_at": expires_at.isoformat()
    }

    db.table("oauth_states").upsert(row).execute()

    print("oauth state saved:", state, discord_id)


def put(state, discord_id, channel_id, message_id, discord_name=None):
    hold(state, discord_id, channel_id, message_id, discord_name)


def take(state):
    cleanup()

    r = db.table("oauth_states").select("*").eq(
        "state",
        str(state)
    ).execute()

    print("oauth state take:", state, r.data)

    if not r.data:
        return None

    row = r.data[0]

    db.table("oauth_states").delete().eq(
        "state",
        str(state)
    ).execute()

    return {
        "discord_id": row["discord_id"],
        "channel_id": row.get("channel_id"),
        "message_id": row.get("message_id"),
        "discord_name": row.get("discord_name")
    }
