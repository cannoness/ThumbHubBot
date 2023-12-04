# bot.py
import asyncio
from time import sleep

import discord
from discord.ext import commands
import os

from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

intent = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intent)


async def load_extensions():
    for filename in os.listdir("./Cogs"):
        if filename.endswith(".py") and '__' not in filename:
            # cut off the .py from the file name
            await bot.load_extension(f"Cogs.{filename[:-3]}")


async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


sleep(3)
asyncio.run(main())
