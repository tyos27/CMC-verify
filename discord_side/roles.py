import requests
from discord_side.client import bot
from core.env import Env
from store.links import pull


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
            out[int(left.strip())] = int(right.strip())
        except Exception:
            pass

    return out


def roblox_rank(user_id):
    url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"

    r = requests.get(url, timeout=15)

    if r.status_code >= 400:
        return 0

    data = r.json().get("data", [])

    for row in data:
        group = row.get("group", {})
        role = row.get("role", {})

        if int(group.get("id", 0)) == Env.roblox_group_id:
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
    user_rank = roblox_rank(roblox_id)
    ranks = rank_map()

    all_rank_role_ids = set(ranks.values())
    current_rank_role_id = ranks.get(user_rank)

    try:
        await member.edit(
            nick=make_nick(saved),
            reason="Roblox verify sync"
        )
    except Exception as e:
        print("nickname edit failed:", e)

    remove_roles = []

    if user_rank != 10:
        for role in member.roles:
            if role.id in all_rank_role_ids and role.id != current_rank_role_id:
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

    if current_rank_role_id:
        current_role = guild.get_role(current_rank_role_id)

        if current_role and current_role not in member.roles:
            add_roles.append(current_role)

    if add_roles:
        try:
            await member.add_roles(
                *add_roles,
                reason="Roblox verify"
            )
        except Exception as e:
            print("role add failed:", e)

    return True, f"{saved['roblox_name']} 계정 인증이 완료되었습니다."
