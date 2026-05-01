from discord_side.client import bot
from core.env import Env
from store.links import pull
from roblox.group import rows


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


def joined_group_ids(user_id):
    targets = set(group_role_map().keys())
    joined = set()

    try:
        data = rows(user_id)
    except Exception as e:
        print("roblox group fetch failed:", e)
        return joined

    for item in data:
        group = item.get("group") or {}

        try:
            group_id = int(group.get("id", 0))
        except Exception:
            continue

        if group_id in targets:
            joined.add(group_id)

    return joined


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
    roles_by_group = group_role_map()
    joined = joined_group_ids(roblox_id)

    if not joined:
        return False, "Roblox 그룹에 가입되어 있지 않습니다."

    all_group_role_ids = set(roles_by_group.values())
    should_have_role_ids = {roles_by_group[group_id] for group_id in joined if group_id in roles_by_group}

    try:
        await member.edit(
            nick=make_nick(saved),
            reason="Roblox verify sync"
        )
    except Exception as e:
        print("nickname edit failed:", e)

    remove_roles = []

    for role in member.roles:
        if role.id in all_group_role_ids and role.id not in should_have_role_ids:
            remove_roles.append(role)

    if remove_roles:
        try:
            await member.remove_roles(
                *remove_roles,
                reason="Roblox group role sync"
            )
        except Exception as e:
            print("group role remove failed:", e)

    add_roles = []

    if base_role not in member.roles:
        add_roles.append(base_role)

    for role_id in should_have_role_ids:
        role = guild.get_role(role_id)

        if role and role not in member.roles:
            add_roles.append(role)

    if add_roles:
        try:
            await member.add_roles(
                *add_roles,
                reason="Roblox verify"
            )
        except Exception as e:
            print("role add failed:", e)

    return True, f"{saved['roblox_name']} 계정 인증이 완료되었습니다."
