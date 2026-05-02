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


def find_group_rows_in_data(data, target_group_id):
    result = []

    for item in data:
        group = item.get("group") or {}

        try:
            group_id = int(group.get("id", 0))
        except Exception:
            continue

        if group_id == int(target_group_id):
            result.append(item)

    return result


def find_group_in_rows(data, target_group_id):
    found = find_group_rows_in_data(data, target_group_id)

    if found:
        return found[0]

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


def get_rank_from_role(role):
    if not isinstance(role, dict):
        return None

    keys = (
        "rank",
        "roleRank",
        "rankId",
        "role_rank",
        "roleRankId"
    )

    for key in keys:
        value = role.get(key)

        if value is None:
            continue

        try:
            return int(value)
        except Exception:
            pass

    return None


def collect_ranks_from_row(row):
    ranks = []

    if not isinstance(row, dict):
        return ranks

    role = row.get("role") or {}

    rank = get_rank_from_role(role)

    if rank is not None:
        ranks.append(rank)

    possible_multi_role_keys = (
        "roles",
        "roleSets",
        "role_sets",
        "assignedRoles",
        "assigned_roles",
        "communityRoles",
        "community_roles"
    )

    for key in possible_multi_role_keys:
        value = row.get(key)

        if isinstance(value, list):
            for role_item in value:
                rank = get_rank_from_role(role_item)

                if rank is not None:
                    ranks.append(rank)

        elif isinstance(value, dict):
            rank = get_rank_from_role(value)

            if rank is not None:
                ranks.append(rank)

    unique = []

    for rank in ranks:
        if rank not in unique:
            unique.append(rank)

    unique.sort()

    return unique


def ranks(user_id):
    data = rows(user_id)
    group_rows = find_group_rows_in_data(data, Env.roblox_maingroup_id)

    result = []

    for row in group_rows:
        for rank in collect_ranks_from_row(row):
            if rank not in result:
                result.append(rank)

    result.sort()

    return result


def inside(user_id):
    data = rows(user_id)

    if find_group_in_rows(data, Env.roblox_maingroup_id):
        return True

    for group_id in configured_optional_group_ids():
        if find_group_in_rows(data, group_id):
            return True

    return False


def rank(user_id):
    found_ranks = ranks(user_id)

    if not found_ranks:
        return 0

    return max(found_ranks)
