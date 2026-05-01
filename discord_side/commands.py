import discord
from discord_side.client import bot
from discord_side.views import Gate
from core.env import Env
from datetime import datetime


def stamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


@bot.event
async def on_ready():
    if getattr(bot, "done_sync", False):
        return

    bot.done_sync = True

    guild = discord.Object(id=Env.guild_id)

    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)

    print(f"ready: {bot.user}")
    print("synced commands:", [cmd.name for cmd in synced])


@bot.tree.command(name="verify", description="Roblox 계정을 인증합니다.")
async def verify(itx: discord.Interaction):
    await itx.response.defer(thinking=False)

    em = discord.Embed(
        title="✅ 계정 인증",
        description="아래 버튼을 눌러 인증을 진행하세요!",
        color=0x57F287
    )
    em.set_footer(text=f"JAD Verify • {stamp()}")

    view = Gate(itx.user.id)

    msg = await itx.followup.send(
        embed=em,
        view=view,
        wait=True
    )

    view.message = msg
