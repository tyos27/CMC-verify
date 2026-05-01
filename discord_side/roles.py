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


def group_role_map():
    result = {}

    if getattr(Env, "roblox_group_roles", None):
        for group_id, role_id in Env.roblox_group_roles:
            result[int(group_id)] = int(role_id)

    return result


def ordered_group_ids():
    if getattr(Env, "roblox_group_roles", None):
        return [group_id for group_id, _ in Env.roblox_group_roles]

    return [Env.roblox_group_id]


def roblox_groups(user_id):
    url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"

    r = requests.get(url, timeout=15)

    if r.status_code >= 400:
        return []

    return r.json().get("data", [])


def joined_configured_groups(user_id):
    targets = set(ordered_group_ids())
    joined = {}

    for row in roblox_groups(user_id):
        group = row.get("group", {})

        try:
            group_id = int(group.get("id", 0))
        except Exception:
            continue

        if group_id in targets:
            joined[group_id] = row

    return joined


def primary_rank(joined):
    for group_id in ordered_group_ids():
        row = joined.get(group_id)

        if not row:
            continue

        role = row.get("role", {})

        try:
            return int(role.get("rank", 0))
        except Exception:
            return 0

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

    joined = joined_configured_groups(roblox_id)

    if not joined:
        return False, "Roblox 그룹에 가입되어 있지 않습니다."

    user_rank = primary_rank(joined)

    group_roles = group_role_map()
    rank_roles = parse_rank_roles()

    all_group_role_ids = set(group_roles.values())

    should_group_role_ids = {
        group_roles[group_id]
        for group_id in joined.keys()
        if group_id in group_roles
    }

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

    if user_rank != 10:
        for role in member.roles:
            if role.id in all_group_role_ids and role.id not in should_group_role_ids:
                remove_roles.append(role)

            if role.id in all_rank_role_ids and role.id not in should_rank_role_ids:
                remove_roles.append(role)

    if remove_roles:
        try:
            await member.remove_roles(
                *remove_roles,
                reason="Roblox rank sync"
            )
        except Exception as e:
            print("rank role remove failed:", e)

    add_roles = []

    if base_role not in member.roles:
        add_roles.append(base_role)

    for role_id in should_group_role_ids:
        role = guild.get_role(role_id)

        if role and role not in member.roles:
            add_roles.append(role)

    for role_id in should_rank_role_ids:
        role = guild.get_role(role_id)

        if role and role not in member.roles:
            add_roles.append(role)

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

    return True, f"{saved['roblox_name']} 계정 인증이 완료되었습니다."
