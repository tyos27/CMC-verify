import requests
from urllib.parse import quote
from core.env import Env


OPEN_CLOUD_BASE = "https://apis.roblox.com/cloud/v2"


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


def open_cloud_headers():
    key = str(getattr(Env, "roblox_cloud_key", "") or "").strip()

    if not key:
        return None

    return {
        "x-api-key": key
    }


def open_cloud_get(url):
    headers = open_cloud_headers()

    if not headers:
        return None

    try:
        r = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        if r.status_code >= 400:
            print("open cloud group.py failed:", r.status_code, r.text)
            return None

        return r.json()
    except Exception as e:
        print("open cloud group.py exception:", e)
        return None


def role_path_id(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if "/" in value:
        value = value.rstrip("/").split("/")[-1]

    try:
        return int(value)
    except Exception:
        return None


def role_path_group_id(value):
    if value is None:
        return None

    value = str(value).strip()
    parts = value.split("/")

    try:
        if "groups" in parts:
            index = parts.index("groups")
            return int(parts[index + 1])
    except Exception:
        pass

    return None


def extract_role_paths_from_membership(membership):
    result = []

    if not isinstance(membership, dict):
        return result

    for key in ("role", "rolePath", "role_path", "primaryRole"):
        value = membership.get(key)

        if isinstance(value, str):
            result.append(value)

        elif isinstance(value, dict):
            nested = value.get("path") or value.get("name") or value.get("id")

            if nested is not None:
                result.append(str(nested))

    for key in (
        "roles",
        "rolePaths",
        "role_paths",
        "assignedRoles",
        "assigned_roles",
        "communityRoles",
        "community_roles",
        "groupRoles",
        "group_roles"
    ):
        value = membership.get(key)

        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    nested = item.get("path") or item.get("name") or item.get("id")

                    if nested is not None:
                        result.append(str(nested))

        elif isinstance(value, dict):
            nested = value.get("path") or value.get("name") or value.get("id")

            if nested is not None:
                result.append(str(nested))

    unique = []

    for value in result:
        if value not in unique:
            unique.append(value)

    return unique


def list_group_roles_open_cloud(group_id):
    result = {}
    token = ""

    while True:
        url = f"{OPEN_CLOUD_BASE}/groups/{group_id}/roles?maxPageSize=20"

        if token:
            url += "&pageToken=" + quote(token, safe="")

        data = open_cloud_get(url)

        if not data:
            break

        roles_data = (
            data.get("groupRoles")
            or data.get("roles")
            or data.get("data")
            or []
        )

        for role in roles_data:
            if not isinstance(role, dict):
                continue

            role_id = role_path_id(
                role.get("path")
                or role.get("name")
                or role.get("id")
            )

            try:
                rank_value = int(role.get("rank"))
            except Exception:
                rank_value = None

            if role_id is not None and rank_value is not None:
                result[role_id] = rank_value

        token = data.get("nextPageToken") or ""

        if not token:
            break

    return result


def list_user_memberships_open_cloud(group_id, user_id):
    result = []
    token = ""

    filter_value = f"user=='users/{user_id}'"
    encoded_filter = quote(filter_value, safe="='")

    while True:
        url = (
            f"{OPEN_CLOUD_BASE}/groups/{group_id}/memberships"
            f"?maxPageSize=100&filter={encoded_filter}"
        )

        if token:
            url += "&pageToken=" + quote(token, safe="")

        data = open_cloud_get(url)

        if not data:
            break

        memberships = (
            data.get("groupMemberships")
            or data.get("memberships")
            or data.get("data")
            or []
        )

        for membership in memberships:
            if isinstance(membership, dict):
                result.append(membership)

        token = data.get("nextPageToken") or ""

        if not token:
            break

    return result


def open_cloud_ranks(user_id):
    group_id = int(Env.roblox_maingroup_id)

    role_map = list_group_roles_open_cloud(group_id)
    memberships = list_user_memberships_open_cloud(group_id, user_id)

    result = []

    for membership in memberships:
        role_paths = extract_role_paths_from_membership(membership)

        for path in role_paths:
            path_group_id = role_path_group_id(path)

            if path_group_id is not None and path_group_id != group_id:
                continue

            role_id = role_path_id(path)

            if role_id is None:
                continue

            rank_value = role_map.get(role_id)

            if rank_value is None:
                continue

            if rank_value not in result:
                result.append(rank_value)

    result.sort()

    return result


def legacy_rank(user_id):
    item = pick(user_id)

    if not item:
        return 0

    role = item.get("role") or {}

    try:
        return int(role.get("rank") or 0)
    except Exception:
        return 0


def ranks(user_id):
    result = open_cloud_ranks(user_id)

    if result:
        return result

    fallback = legacy_rank(user_id)

    if fallback > 0:
        return [fallback]

    return []


def inside(user_id):
    data = rows(user_id)

    if find_group_in_rows(data, Env.roblox_maingroup_id):
        return True

    for group_id in configured_optional_group_ids():
        if find_group_in_rows(data, group_id):
            return True

    return False


def rank(user_id):
    found = ranks(user_id)

    if not found:
        return 0

    return max(found)
