import asyncio
import threading
import uvicorn
from core.env import Env
from core.site import app
from discord_side.client import bot
import discord_side.commands

def web():
    uvicorn.run(app, host=Env.web_host, port=Env.web_port, log_level="warning")


def run():
    threading.Thread(target=web, daemon=True).start()
    bot.run(Env.token)
