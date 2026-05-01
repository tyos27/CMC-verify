import os
import aiohttp
from discord_side.client import bot
from store.links import get

DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
DISCORD_ROLE_ID = int(os.getenv("DISCORD_ROLE_ID", "0"))
ROBLOX_MAINGROUP_ID = int(os.getenv("ROBLOX_MAINGROUP_ID", "0"))

def parse_rank_roles():
    raw = os.getenv("ROBLOX_RANK_ROLES", "")
    result = []

    for part in raw.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue

        rank_text, role_text = part.split(":", 1)

        try:
            rank = int(rank_text.strip())
            role_id = int(role_text.strip())
        except:
            continue

        result.append((rank, role_id))

    result.sort(key=lambda x: x[0])
    return result

ROBLOX_RANK_ROLES = parse_rank_roles()

async def get_roblox_rank(roblox_id):
    if not ROBLOX_MAINGROUP_ID:
        return 0

    url = f"https://groups.roblox.com/v2/users/{roblox_id}/groups/roles"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            if res.status != 200:
                return 0

            data = await res.json()

    for item in data.get("data", []):
        group = item.get("group", {})
        role = item.get("role", {})

        if int(group.get("id", 0)) == ROBLOX_MAINGROUP_ID:
            return int(role.get("rank", 0))

    return 0

def get_rank_role_ids(rank):
    role_ids = []

    for required_rank, role_id in ROBLOX_RANK_ROLES:
        if rank >= required_rank:
            role_ids.append(role_id)

    return role_ids

async def refresh(discord_id):
    link = get(str(discord_id))

    if not link:
        return False, "연동 정보를 찾지 못했습니다."

    roblox_id = link.get("roblox_id")

    if not roblox_id:
        return False, "Roblox ID를 찾지 못했습니다."

    guild = bot.get_guild(DISCORD_GUILD_ID)

    if not guild:
        return False, "Discord 서버를 찾지 못했습니다."

    member = guild.get_member(int(discord_id))

    if not member:
        try:
            member = await guild.fetch_member(int(discord_id))
        except:
            return False, "Discord 멤버를 찾지 못했습니다."

    add_roles = []

    if DISCORD_ROLE_ID:
        base_role = guild.get_role(DISCORD_ROLE_ID)
        if base_role:
            add_roles.append(base_role)

    rank = await get_roblox_rank(roblox_id)
    rank_role_ids = get_rank_role_ids(rank)
    managed_role_ids = [role_id for _, role_id in ROBLOX_RANK_ROLES]

    for role_id in rank_role_ids:
        role = guild.get_role(role_id)
        if role:
            add_roles.append(role)

    remove_roles = []

    for role_id in managed_role_ids:
        if role_id not in rank_role_ids:
            role = guild.get_role(role_id)
            if role and role in member.roles:
                remove_roles.append(role)

    if add_roles:
        await member.add_roles(*add_roles, reason="Roblox verification rank sync")

    if remove_roles:
        await member.remove_roles(*remove_roles, reason="Roblox verification rank sync")

    return True, f"인증 완료. Roblox rank: {rank}"
