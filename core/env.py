import os
from dotenv import load_dotenv

load_dotenv()


def pick(name, cast=str, default=None):
    value = os.getenv(name)
    if value is None or value == "":
        if default is not None:
            return default
        raise RuntimeError(f"missing env: {name}")
    return cast(value)


class Env:
    token = pick("DISCORD_TOKEN")
    guild_id = pick("DISCORD_GUILD_ID", int)
    role_id = pick("DISCORD_ROLE_ID", int)

    supabase_url = pick("SUPABASE_URL")
    supabase_key = pick("SUPABASE_KEY")

    roblox_client_id = pick("ROBLOX_CLIENT_ID")
    roblox_client_secret = pick("ROBLOX_CLIENT_SECRET")
    roblox_redirect = pick("ROBLOX_REDIRECT_URI")
    roblox_group_id = pick("ROBLOX_GROUP_ID", int)

    site_url = pick("SITE_URL")

    web_host = pick("WEB_HOST", str, "0.0.0.0")
    web_port = pick("WEB_PORT", int, 8000)

    tag = pick("DISCORD_GROUP_TAG", str, "")
    rank_roles = pick("ROBLOX_RANK_ROLES", str, "")


    game_api_key = pick("GAME_API_KEY")
