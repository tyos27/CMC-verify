import requests
from urllib.parse import quote
from discord_side.client import bot
from core.env import Env
from store.links import pull


OPEN_CLOUD_BASE = "https://apis.roblox.com/cloud/v2"


def parse_rank_roles():
    out = {}

    raw = Env.rank_roles

    for row in raw.split(","):
        row = row.strip()

        if not row:
            continue

        if ":" not in row:
            continue

        left, right = row.split(":", 1)

        try:
            rank = int(left.strip())
            role_id = int(right.strip())
        except Exception:
            continue

        if rank not in out:
            out[rank] = []

        if role_id not in out[rank]:
            out[rank].append(role_id)

    return out


def parse_rank_tags():
    out = {}

    raw = Env.rank_tags

    for row in raw.split(","):
        row = row.strip()

        if not row:
            continue

        if ":" not in row:
            continue

        left, right = row.split(":", 1)

        try:
            rank = int(left.strip())
            tag = str(right).strip()
        except Exception:
            continue

        if not tag:
            continue

        if rank not in out:
            out[rank] = []

        if tag not in out[rank]:
            out[rank].append(tag)

    return out


def optional_groups():
    result = []

    for item in Env.roblox_group_roles:
        try:
            result.append({
                "group_id": int(item["group_id"]),
                "role_id": int(item["role_id"]),
                "label": str(item.get("label") or "").strip()
            })
        except Exception:
            pass

    return result


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
        print("open cloud skipped: ROBLOX_CLOUD_KEY missing")
        return None

    try:
        r = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        if r.status_code >= 400:
            print("open cloud failed:", r.status_code, r.text)
            return None

        return r.json()
    except Exception as e:
        print("open cloud request failed:", e)
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

    possible_single_keys = (
        "role",
        "rolePath",
        "role_path",
        "primaryRole"
    )

    possible_multi_keys = (
        "roles",
        "rolePaths",
        "role_paths",
        "assignedRoles",
        "assigned_roles",
        "communityRoles",
        "community_roles",
        "groupRoles",
        "group_roles"
    )

    for key in possible_single_keys:
        value = membership.get(key)

        if isinstance(value, str):
            result.append(value)

        elif isinstance(value, dict):
            nested = value.get("path") or value.get("name") or value.get("id")

            if nested is not None:
                result.append(str(nested))

    for key in possible_multi_keys:
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

        roles = (
            data.get("groupRoles")
            or data.get("roles")
            or data.get("data")
            or []
        )

        for role in roles:
            if not isinstance(role, dict):
                continue

            role_id = role_path_id(
                role.get("path")
                or role.get("name")
                or role.get("id")
            )

            try:
                rank = int(role.get("rank"))
            except Exception:
                rank = None

            if role_id is not None and rank is not None:
                result[role_id] = {
                    "rank": rank,
                    "name": str(
                        role.get("displayName")
                        or role.get("name")
                        or role.get("id")
                        or role_id
                    )
                }

        token = data.get("nextPageToken") or ""

        if not token:
            break

    print("open cloud group roles loaded:", group_id, result)

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

    print("open cloud memberships loaded:", group_id, user_id, result)

    return result


def get_main_group_ranks_open_cloud(user_id):
    group_id = int(Env.roblox_maingroup_id)

    role_map = list_group_roles_open_cloud(group_id)
    memberships = list_user_memberships_open_cloud(group_id, user_id)

    ranks = []

    for membership in memberships:
        role_paths = extract_role_paths_from_membership(membership)

        print("membership role paths:", role_paths)

        for path in role_paths:
            path_group_id = role_path_group_id(path)

            if path_group_id is not None and path_group_id != group_id:
                continue

            role_id = role_path_id(path)

            if role_id is None:
                continue

            role_info = role_map.get(role_id)

            if not role_info:
                print("role id not found in role map:", role_id)
                continue

            rank = int(role_info["rank"])

            if rank not in ranks:
                ranks.append(rank)

    ranks.sort()

    print("open cloud main group ranks detected:", ranks)

    return ranks


def roblox_groups_legacy(user_id):
    url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"

    try:
        r = requests.get(url, timeout=15)

        if r.status_code >= 400:
            print("legacy roblox group api failed:", r.status_code, r.text)
            return []

        return r.json().get("data", [])
    except Exception as e:
        print("legacy roblox group api exception:", e)
        return []


def get_legacy_group_rows(user_id):
    result = {}

    for item in roblox_groups_legacy(user_id):
        group = item.get("group") or {}

        try:
            group_id = int(group.get("id", 0))
        except Exception:
            continue

        result[group_id] = item

    return result


def get_legacy_rank_from_group_row(row):
    if not row:
        return 0

    role = row.get("role") or {}

    try:
        return int(role.get("rank") or 0)
    except Exception:
        return 0


def clean(value):
    if value is None:
        return ""

    value = str(value).strip()

    if value.lower() in ("none", "null"):
        return ""

    return value


def default_tag():
    tag = Env.tag.strip()

    if ":" in tag or "," in tag:
        return ""

    return tag


def first_joined_optional_label(group_rows):
    for item in optional_groups():
        group_id = item["group_id"]

        if group_id in group_rows:
            label = item.get("label") or ""

            if label:
                return label

            row = group_rows.get(group_id) or {}
            group = row.get("group") or {}
            return str(group.get("name") or group_id)

    return ""


def make_nick(saved, user_ranks, main_joined, group_rows):
    username = clean(saved.get("roblox_name"))
    display = clean(saved.get("roblox_display_name"))

    if display and display != username:
        name = f"({display}) {username}"
    else:
        name = username

    prefix = ""

    if main_joined:
        rank_tags = parse_rank_tags()
        tags = []

        for rank in user_ranks:
            for tag in rank_tags.get(rank, []):
                if tag not in tags:
                    tags.append(tag)

        if tags:
            prefix = "".join(f"[{tag}]" for tag in tags)
        else:
            tag = default_tag()

            if tag:
                prefix = f"[{tag}]"
    else:
        label = first_joined_optional_label(group_rows)

        if label:
            prefix = f"[{label}]"

    if prefix:
        nick = f"{prefix} {name}"
    else:
        nick = name

    return nick[:32]


def exact_rank_role_ids(rank_roles, user_ranks):
    result = set()

    for rank in user_ranks:
        for role_id in rank_roles.get(rank, []):
            result.add(role_id)

    return result


async def refresh(discord_id):
    saved = pull(discord_id)

    if not saved:
        return False, "연동 기록이 없습니다."

    guild = bot.get_guild(Env.guild_id)

    if not guild:
        return False, "서버를 찾지 못했습니다."

    member = guild.get_member(int(discord_id))

    if not member:
        try:
            member = await guild.fetch_member(int(discord_id))
        except Exception:
            return False, "멤버를 찾지 못했습니다."

    base_role = guild.get_role(Env.role_id)

    if not base_role:
        return False, "기본 역할을 찾지 못했습니다."

    roblox_id = int(saved["roblox_id"])

    legacy_group_rows = get_legacy_group_rows(roblox_id)

    main_group_id = int(Env.roblox_maingroup_id)
    main_joined = main_group_id in legacy_group_rows

    joined_optional = []

    for item in optional_groups():
        if item["group_id"] in legacy_group_rows:
            joined_optional.append(item)

    if not main_joined and not joined_optional:
        print("no valid roblox group joined")
        print("main group:", Env.roblox_maingroup_id)
        print("joined roblox groups:", list(legacy_group_rows.keys()))
        return False, "Roblox 메인 그룹 또는 인증 가능한 부서 그룹에 가입되어 있지 않습니다."

    user_ranks = []

    if main_joined:
        user_ranks = get_main_group_ranks_open_cloud(roblox_id)

        if not user_ranks:
            legacy_rank = get_legacy_rank_from_group_row(
                legacy_group_rows.get(main_group_id)
            )

            if legacy_rank > 0:
                user_ranks = [legacy_rank]

            print("open cloud ranks empty, fallback legacy rank:", user_ranks)

    print("main group joined:", main_joined)
    print("final main group ranks detected:", user_ranks)

    rank_roles = parse_rank_roles()

    all_optional_role_ids = set()

    for item in optional_groups():
        all_optional_role_ids.add(item["role_id"])

    should_optional_role_ids = set()

    for item in joined_optional:
        should_optional_role_ids.add(item["role_id"])

    all_rank_role_ids = set()

    for role_ids in rank_roles.values():
        for role_id in role_ids:
            all_rank_role_ids.add(role_id)

    should_rank_role_ids = set()

    if main_joined:
        should_rank_role_ids = exact_rank_role_ids(rank_roles, user_ranks)

    print("should rank discord roles:", list(should_rank_role_ids))
    print("should optional discord roles:", list(should_optional_role_ids))

    try:
        await member.edit(
            nick=make_nick(saved, user_ranks, main_joined, legacy_group_rows),
            reason="Roblox verify sync"
        )
    except Exception as e:
        print("nickname edit failed:", e)

    remove_roles = []

    for role in member.roles:
        if role.id in all_optional_role_ids and role.id not in should_optional_role_ids:
            remove_roles.append(role)

        if role.id in all_rank_role_ids and role.id not in should_rank_role_ids:
            remove_roles.append(role)

    if remove_roles:
        try:
            await member.remove_roles(
                *remove_roles,
                reason="Roblox role sync"
            )
        except Exception as e:
            print("role remove failed:", e)

    add_roles = []

    if base_role not in member.roles:
        add_roles.append(base_role)

    for role_id in should_optional_role_ids:
        role = guild.get_role(role_id)

        if role and role not in member.roles:
            add_roles.append(role)

        if not role:
            print("optional discord role not found:", role_id)

    for role_id in should_rank_role_ids:
        role = guild.get_role(role_id)

        if role and role not in member.roles:
            add_roles.append(role)

        if not role:
            print("rank discord role not found:", role_id)

    unique_add_roles = []
    seen = set()

    for role in add_roles:
        if role.id in seen:
            continue

        seen.add(role.id)
        unique_add_roles.append(role)

    if unique_add_roles:
        try:
            await member.add_roles(
                *unique_add_roles,
                reason="Roblox verify"
            )
        except Exception as e:
            print("role add failed:", e)
            return False, "역할 지급에 실패했습니다. 봇 역할 위치나 권한을 확인해주세요."

    return True, f"{saved['roblox_name']} 계정 인증이 완료되었습니다."
