from discord_side.client import bot
from core.env import Env
from store.links import pull
from roblox.group import rows


def rank_map():
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
        except Exception as e:
            print("rank map parse failed:", row, e)
            continue

        if rank not in out:
            out[rank] = []

        if role_id not in out[rank]:
            out[rank].append(role_id)

    return out


def clean(value):
    if value is None:
        return ""

    value = str(value).strip()

    if value.lower() in ("none", "null"):
        return ""

    return value


def make_nick(saved):
    tag = Env.tag.strip()

    username = clean(saved.get("roblox_name"))
    display = clean(saved.get("roblox_display_name"))

    if display and display != username:
        name = f"({display}) {username}"
    else:
        name = username

    if tag:
        nick = f"[{tag}] {name}"
    else:
        nick = name

    return nick[:32]


def group_role_map():
    result = {}

    for group_id, role_id in Env.roblox_group_roles:
        result[int(group_id)] = int(role_id)

    return result


def ordered_group_ids():
    return [int(group_id) for group_id, _ in Env.roblox_group_roles]


def get_joined_groups(user_id):
    targets = set(group_role_map().keys())
    joined = {}

    try:
        data = rows(user_id)
    except Exception as e:
        print("roblox group fetch failed:", e)
        return joined

    print("configured roblox groups:", list(targets))

    for item in data:
        group = item.get("group") or {}
        role = item.get("role") or {}

        try:
            group_id = int(group.get("id", 0))
            rank = int(role.get("rank", 0))
        except Exception:
            continue

        print("roblox group row:", group_id, "rank:", rank)

        if group_id in targets:
            joined[group_id] = item

    print("joined configured groups:", list(joined.keys()))

    return joined


def get_primary_rank(joined):
    for group_id in ordered_group_ids():
        item = joined.get(group_id)

        if not item:
            continue

        role = item.get("role") or {}

        try:
            return int(role.get("rank") or 0)
        except Exception:
            return 0

    return 0


async def refresh(discord_id):
    print("refresh start:", discord_id)

    saved = pull(discord_id)

    if not saved:
        print("refresh failed: no saved verify")
        return False, "연동 기록이 없습니다."

    guild = bot.get_guild(Env.guild_id)

    if not guild:
        print("refresh failed: guild not found", Env.guild_id)
        return False, "서버를 찾지 못했습니다."

    member = guild.get_member(int(discord_id))

    if not member:
        try:
            member = await guild.fetch_member(int(discord_id))
        except Exception as e:
            print("refresh failed: member not found", discord_id, e)
            return False, "멤버를 찾지 못했습니다."

    base_role = guild.get_role(Env.role_id)

    if not base_role:
        print("refresh failed: base role not found", Env.role_id)
        return False, "기본 역할을 찾지 못했습니다."

    roblox_id = int(saved["roblox_id"])

    roles_by_group = group_role_map()
    joined = get_joined_groups(roblox_id)

    if not joined:
        print("refresh failed: not in configured roblox groups")
        return False, "Roblox 그룹에 가입되어 있지 않습니다."

    ranks = rank_map()
    user_rank = get_primary_rank(joined)

    print("primary roblox rank:", user_rank)
    print("rank map:", ranks)

    all_group_role_ids = set(roles_by_group.values())

    should_have_group_role_ids = {
        roles_by_group[group_id]
        for group_id in joined.keys()
        if group_id in roles_by_group
    }

    all_rank_role_ids = set()

    for role_ids in ranks.values():
        for role_id in role_ids:
            all_rank_role_ids.add(role_id)

    should_have_rank_role_ids = set(ranks.get(user_rank, []))

    print("should have group roles:", should_have_group_role_ids)
    print("should have rank roles:", should_have_rank_role_ids)

    try:
        await member.edit(
            nick=make_nick(saved),
            reason="Roblox verify sync"
        )

        print("nickname updated")
    except Exception as e:
        print("nickname edit failed:", e)

    remove_roles = []

    for role in member.roles:
        if role.id in all_group_role_ids and role.id not in should_have_group_role_ids:
            remove_roles.append(role)

        if role.id in all_rank_role_ids and role.id not in should_have_rank_role_ids:
            remove_roles.append(role)

    if remove_roles:
        try:
            await member.remove_roles(
                *remove_roles,
                reason="Roblox role sync"
            )

            print("removed roles:", [role.id for role in remove_roles])
        except Exception as e:
            print("role remove failed:", e)

    add_roles = []

    if base_role not in member.roles:
        add_roles.append(base_role)

    for role_id in should_have_group_role_ids:
        role = guild.get_role(role_id)

        if role and role not in member.roles:
            add_roles.append(role)

        if not role:
            print("group discord role not found:", role_id)

    for role_id in should_have_rank_role_ids:
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

            print("added roles:", [role.id for role in unique_add_roles])
        except Exception as e:
            print("role add failed:", e)
            return False, "역할 지급에 실패했습니다. 봇 역할 위치나 권한을 확인해주세요."

    print("refresh success:", discord_id)

    return True, f"{saved['roblox_name']} 계정 인증이 완료되었습니다."
