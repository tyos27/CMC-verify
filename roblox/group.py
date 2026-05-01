import requests
from core.env import Env


def rows(user_id):
    r = requests.get(
        f"https://groups.roblox.com/v2/users/{user_id}/groups/roles",
        timeout=15
    )
    r.raise_for_status()
    return r.json().get("data", [])


def configured_group_ids():
    if getattr(Env, "roblox_group_roles", None):
        return [group_id for group_id, _ in Env.roblox_group_roles]

    return [Env.roblox_group_id]


def pick(user_id):
    group_ids = configured_group_ids()

    data = rows(user_id)

    for target_id in group_ids:
        for item in data:
            g = item.get("group") or {}

            try:
                group_id = int(g.get("id", 0))
            except Exception:
                continue

            if group_id == int(target_id):
                return item

    return None


def inside(user_id):
    return pick(user_id) is not None


def rank(user_id):
    item = pick(user_id)

    if not item:
        return 0

    role = item.get("role") or {}

    try:
        return int(role.get("rank") or 0)
    except Exception:
        return 0
