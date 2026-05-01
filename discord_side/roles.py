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


def optional_group_role_map():
    result = {}

    for group_id, role_id in Env.roblox_group_roles:
        result[int(group_id)] = int(role_id)

    return result


def roblox_groups(user_id):
    url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"

    r = requests.get(url, timeout=15)

    if r.status_code >= 400:
        print("roblox group api failed:", r.status_code, r.text)
        return []

    return r.json().get("data", [])


def get_group_rows(user_id):
    rows = {}

    for item in roblox_groups(user_id):
        group = item.get("group") or {}

        try:
            group_id = int(group.get("id", 0))
        except Exception:
            continue

        rows[group_id] = item

    return rows


def get_rank_from_group_row(row):
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


def make_nick(saved, user_rank):
    username = clean(saved.get("roblox_name"))
    display = clean(saved.get("roblox_display_name"))

    if display and display != username:
        name = f"({display}) {username}"
    else:
        name = username

    tags = parse_rank_tags().get(user_rank, [])

    if tags:
        prefix = "".join(f"[{tag}]" for tag in tags)
        nick = f"{prefix} {name}"
    else:
        tag = Env.tag.strip()

        if tag:
            nick = f"[{tag}] {name}"
        else:
            nick = name

    return nick[:32]


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

    main_group_row = group_rows.get(int(Env.roblox_maingroup_id))

    if not main_group_row:
        print("main group not joined:", Env.roblox_maingroup_id, "roblox:", roblox_id)
        print("joined roblox groups:", list(group_rows.keys()))
        return False, "Roblox 메인 그룹에 가입되어 있지 않습니다."

    user_rank = get_rank_from_group_row(main_group_row)

    optional_groups = optional_group_role_map()
    rank_roles = parse_rank_roles()

    all_optional_role_ids = set(optional_groups.values())

    should_optional_role_ids = set()

    for group_id, discord_role_id in optional_groups.items():
        if group_id in group_rows:
            should_optional_role_ids.add(discord_role_id)

    all_rank_role_ids = set()

    for ids in rank_roles.values():
        for role_id in ids:
            all_rank_role_ids.add(role_id)

    should_rank_role_ids = set(rank_roles.get(user_rank, []))

    try:
        await member.edit(
            nick=make_nick(saved, user_rank),
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
