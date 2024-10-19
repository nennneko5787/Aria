import asyncio
import os

import discord
import dotenv
from discord.ext import commands, tasks

dotenv.load_dotenv()

intents = discord.Intents.default()
bot = commands.Bot([], intents=intents)


@tasks.loop(hours=1)
async def presence():
    appInfo = await bot.application_info()
    await bot.change_presence(
        activity=discord.Game(
            f"{appInfo.approximate_guild_count} guilds and {appInfo.approximate_user_install_count} users"
        )
    )


@bot.event
async def on_ready():
    presence.start()


@bot.event
async def setup_hook():
    await bot.load_extension("cogs.chat")
    await bot.load_extension("cogs.picgen")
    await bot.tree.sync()


bot.run(os.getenv("discord"))
