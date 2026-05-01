import threading
import traceback
import uvicorn

from core.env import Env
from core.site import app
from discord_side.client import bot
import discord_side.commands


def web():
    try:
        print(f"starting web server on {Env.web_host}:{Env.web_port}")
        uvicorn.run(
            app,
            host=Env.web_host,
            port=Env.web_port,
            log_level="info"
        )
    except Exception:
        print("web server crashed")
        traceback.print_exc()


def run():
    thread = threading.Thread(
        target=web,
        daemon=True
    )

    thread.start()

    print("starting discord bot")
    bot.run(Env.token)
