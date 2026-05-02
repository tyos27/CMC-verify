import requests
from core.env import Env


def rows(user_id):
    r = requests.get(
        f"https://groups.roblox.com/v2/users/{user_id}/groups/roles",
        timeout=15
    )

    r.raise_for_status()

    return r.json().get("data", [])


def configured_optional_group_ids():
    result = []

    for item in Env.roblox_group_roles:
        try:
            result.append(int(item["group_id"]))
        except Exception:
            pass

    return result


def find_group_in_rows(data, target_group_id):
    for item in data:
        group = item.get("group") or {}

        try:
            group_id = int(group.get("id", 0))
        except Exception:
            continue

        if group_id == int(target_group_id):
            return item

    return None


def find_group(user_id, target_group_id):
    return find_group_in_rows(rows(user_id), target_group_id)


def pick(user_id):
    return find_group(user_id, Env.roblox_maingroup_id)


def pick_optional(user_id):
    data = rows(user_id)

    for group_id in configured_optional_group_ids():
        item = find_group_in_rows(data, group_id)

        if item:
            return item

    return None


def inside(user_id):
    data = rows(user_id)

    if find_group_in_rows(data, Env.roblox_maingroup_id):
        return True

    for group_id in configured_optional_group_ids():
        if find_group_in_rows(data, group_id):
            return True

    return False


def rank(user_id):
    item = pick(user_id)

    if not item:
        return 0

    role = item.get("role") or {}

    try:
        return int(role.get("rank") or 0)
    except Exception:
        return 0
