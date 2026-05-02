import requests
from discord_side.client import bot
from core.env import Env
from store.links import pull


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


def roblox_groups(user_id):
    url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"

    r = requests.get(url, timeout=15)

    if r.status_code >= 400:
        print("roblox group api failed:", r.status_code, r.text)
        return []

    data = r.json().get("data", [])

    print("roblox groups raw count:", len(data))

    return data


def get_group_rows(user_id):
    result = {}

    for item in roblox_groups(user_id):
        group = item.get("group") or {}

        try:
            group_id = int(group.get("id", 0))
        except Exception:
            continue

        if group_id not in result:
            result[group_id] = []

        result[group_id].append(item)

    return result


def get_group_first_row(group_rows, group_id):
    rows = group_rows.get(int(group_id), [])

    if not rows:
        return None

    return rows[0]


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


def get_ranks_from_group_rows(group_rows, group_id):
    ranks = []

    rows = group_rows.get(int(group_id), [])

    for row in rows:
        for rank in collect_ranks_from_row(row):
            if rank not in ranks:
                ranks.append(rank)

    ranks.sort()

    return ranks


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

            rows = group_rows.get(group_id) or []
            row = rows[0] if rows else {}
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

    group_rows = get_group_rows(roblox_id)

    main_group_id = int(Env.roblox_maingroup_id)
    main_group_row = get_group_first_row(group_rows, main_group_id)
    main_joined = main_group_row is not None

    joined_optional = []

    for item in optional_groups():
        if item["group_id"] in group_rows:
            joined_optional.append(item)

    if not main_joined and not joined_optional:
        print("no valid roblox group joined")
        print("main group:", Env.roblox_maingroup_id)
        print("joined roblox groups:", list(group_rows.keys()))
        return False, "Roblox 메인 그룹 또는 인증 가능한 부서 그룹에 가입되어 있지 않습니다."

    user_ranks = []

    if main_joined:
        user_ranks = get_ranks_from_group_rows(group_rows, main_group_id)

    print("main group joined:", main_joined)
    print("main group ranks detected:", user_ranks)

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
            nick=make_nick(saved, user_ranks, main_joined, group_rows),
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
