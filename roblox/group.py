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
    return [group_id for group_id, _ in Env.roblox_group_roles]


def matched(user_id):
    ids = set(configured_group_ids())
    result = []

    for item in rows(user_id):
        group = item.get("group") or {}

        try:
            group_id = int(group.get("id", 0))
        except Exception:
            continue

        if group_id in ids:
            result.append(item)

    return result


def pick(user_id):
    data = matched(user_id)

    if not data:
        return None

    order = configured_group_ids()

    for group_id in order:
        for item in data:
            group = item.get("group") or {}

            try:
                current_id = int(group.get("id", 0))
            except Exception:
                continue

            if current_id == group_id:
                return item

    return data[0]


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
