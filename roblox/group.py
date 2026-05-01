import requests
from core.env import Env


def rows(user_id):
    r = requests.get(
        f"https://groups.roblox.com/v2/users/{user_id}/groups/roles",
        timeout=15
    )

    r.raise_for_status()

    return r.json().get("data", [])


def find_group(user_id, target_group_id):
    for item in rows(user_id):
        group = item.get("group") or {}

        try:
            group_id = int(group.get("id", 0))
        except Exception:
            continue

        if group_id == int(target_group_id):
            return item

    return None


def pick(user_id):
    return find_group(user_id, Env.roblox_maingroup_id)


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
