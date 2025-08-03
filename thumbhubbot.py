# bot.py
import asyncio
import os
import discord

from discord.ext import commands

from Settings.config import Config, ApiUrl, Cooldown, MaxImageCount, Role, RoleSet

CONFIG = Config()
APIURL = ApiUrl()
COOLDOWN = Cooldown()
MAXCOUNT = MaxImageCount()
ROLE = Role()
ROLESET = RoleSet()

intent = discord.Intents.all()

TOKEN = os.getenv("TOKEN")  # TODO: need to move this to secrets manager

bot = commands.Bot(command_prefix="!", intents=intent, help_command=None)


async def load_extensions():
    for filename in os.listdir("./Cogs"):
        if filename.endswith(".py") and '__' not in filename:
            # cut off the .py from the file name
            await bot.load_extension(f"Cogs.{filename[:-3]}")


async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


asyncio.run(main())
