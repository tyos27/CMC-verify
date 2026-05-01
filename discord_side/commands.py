import discord
from discord_side.client import bot
from discord_side.views import Gate
from core.env import Env
from datetime import datetime


def stamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


@bot.event
async def on_ready():
    if getattr(bot, "done_ready", False):
        return

    bot.done_ready = True

    print(f"ready: {bot.user}")
    print(f"guild id: {Env.guild_id}")

    if str(Env.sync_commands).lower() in ("1", "true", "yes", "on"):
        guild = discord.Object(id=Env.guild_id)

        try:
            synced = await bot.tree.sync(guild=guild)
            print("synced commands:", [cmd.name for cmd in synced])
        except Exception as e:
            print("command sync failed:", e)


@bot.tree.command(
    name="verify",
    description="Roblox 계정을 인증합니다.",
    guild=discord.Object(id=Env.guild_id)
)
async def verify(itx: discord.Interaction):
    try:
        await itx.response.defer(thinking=False)
    except Exception as e:
        print("verify defer failed:", e)
        return

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
