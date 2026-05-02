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


def normalize_url(value):
    value = str(value or "").strip().rstrip("/")

    if not value:
        return value

    if not value.startswith(("http://", "https://")):
        value = "https://" + value

    return value


def parse_optional_group_roles():
    items = []

    for key, value in os.environ.items():
        if not key.startswith("ROBLOX_GROUP_ID"):
            continue

        value = str(value or "").strip()

        if not value:
            continue

        parts = value.split(":", 2)

        if len(parts) < 2:
            continue

        try:
            group_id = int(parts[0].strip())
            discord_role_id = int(parts[1].strip())
        except Exception:
            continue

        label = ""

        if len(parts) >= 3:
            label = str(parts[2]).strip()

        suffix = key.replace("ROBLOX_GROUP_ID", "")

        if suffix.isdigit():
            order = int(suffix)
        else:
            order = 999999

        items.append({
            "order": order,
            "group_id": group_id,
            "role_id": discord_role_id,
            "label": label
        })

    items.sort(key=lambda x: x["order"])

    return items


class Env:
    token = pick("DISCORD_TOKEN")
    guild_id = pick("DISCORD_GUILD_ID", int)
    role_id = pick("DISCORD_ROLE_ID", int)

    supabase_url = pick("SUPABASE_URL")
    supabase_key = pick("SUPABASE_KEY")

    site_url = normalize_url(pick("SITE_URL"))

    roblox_client_id = pick("ROBLOX_CLIENT_ID")
    roblox_client_secret = pick("ROBLOX_CLIENT_SECRET")

    roblox_redirect = normalize_url(
        pick("ROBLOX_REDIRECT_URI", str, site_url + "/oauth/callback")
    )

    roblox_maingroup_id = pick("ROBLOX_MAINGROUP_ID", int)
    roblox_group_id = roblox_maingroup_id

    roblox_group_roles = parse_optional_group_roles()

    web_host = "0.0.0.0"
    web_port = int(os.getenv("PORT") or os.getenv("WEB_PORT") or "8000")

    tag = pick("DISCORD_GROUP_TAG", str, "")
    rank_roles = pick("ROBLOX_RANK_ROLES", str, "")
    rank_tags = pick("ROBLOX_RANK_TAGS", str, "")

    roblox_cloud_key = pick("ROBLOX_CLOUD_KEY", str, "")
    rank_staff_roles = pick("RANK_STAFF_ROLES", str, "")

    game_api_key = pick("GAME_API_KEY")
    sync_commands = pick("SYNC_COMMANDS", str, "0")
