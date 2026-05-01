import requests
from core.env import Env


def rows(user_id):
    r = requests.get(
        f"https://groups.roblox.com/v2/users/{user_id}/groups/roles",
        timeout=15
    )
    r.raise_for_status()
    return r.json().get("data", [])


def pick(user_id):
    for item in rows(user_id):
        g = item.get("group") or {}
        if int(g.get("id", 0)) == int(Env.roblox_group_id):
            return item
    return None


def inside(user_id):
    return pick(user_id) is not None


def rank(user_id):
    item = pick(user_id)
    if not item:
        return 0

    role = item.get("role") or {}
    return int(role.get("rank") or 0)
