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


def parse_roblox_group_roles():
    items = []

    for key, value in os.environ.items():
        if not key.startswith("ROBLOX_GROUP_ID"):
            continue

        value = str(value or "").strip()

        if not value:
            continue

        if ":" not in value:
            raise RuntimeError(f"invalid env: {key}")

        group_id, role_id = value.split(":", 1)

        try:
            group_id = int(group_id.strip())
            role_id = int(role_id.strip())
        except Exception:
            raise RuntimeError(f"invalid env: {key}")

        items.append((key, group_id, role_id))

    def sort_key(item):
        suffix = item[0].replace("ROBLOX_GROUP_ID", "")

        if suffix.isdigit():
            return int(suffix)

        return 999999

    items.sort(key=sort_key)

    result = [(group_id, role_id) for _, group_id, role_id in items]

    if not result:
        raise RuntimeError("missing env: ROBLOX_GROUP_ID1")

    return result


class Env:
    token = pick("DISCORD_TOKEN")
    guild_id = pick("DISCORD_GUILD_ID", int)
    role_id = pick("DISCORD_ROLE_ID", int)

    supabase_url = pick("SUPABASE_URL")
    supabase_key = pick("SUPABASE_KEY")

    roblox_client_id = pick("ROBLOX_CLIENT_ID")
    roblox_client_secret = pick("ROBLOX_CLIENT_SECRET")
    roblox_redirect = pick("ROBLOX_REDIRECT_URI")

    roblox_group_roles = parse_roblox_group_roles()
    rank_roles = pick("ROBLOX_RANK_ROLES", str, "")
    rank_tags = pick("ROBLOX_RANK_TAGS", str, "")

    site_url = pick("SITE_URL")

    web_host = pick("WEB_HOST", str, "0.0.0.0")
    web_port = pick("PORT", int, pick("WEB_PORT", int, 8000))

    tag = pick("DISCORD_GROUP_TAG", str, "")

    game_api_key = pick("GAME_API_KEY")
