from supabase import create_client
from core.env import Env

db = create_client(Env.supabase_url, Env.supabase_key)


def pull(discord_id):
    r = db.table("verifies").select("*").eq(
        "discord_id",
        str(discord_id)
    ).execute()

    if r.data:
        print("pull verify found:", discord_id, r.data[0])
        return r.data[0]

    print("pull verify not found:", discord_id)
    return None


def put(discord_id, roblox_id, roblox_name, roblox_display_name=None):
    db.table("verifies").upsert({
        "discord_id": str(discord_id),
        "roblox_id": str(roblox_id),
        "roblox_name": str(roblox_name),
        "roblox_display_name": str(roblox_display_name) if roblox_display_name else None
    }).execute()
