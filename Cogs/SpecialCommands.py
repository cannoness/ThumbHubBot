from Utilities.DA_rest import DARest
from discord.ext import commands
import discord
import os
import random

from dotenv import load_dotenv

load_dotenv()
ART_LIT_CHANNEL = os.getenv("ART_LIT_CHANNEL")
BOT_TESTING_CHANNEL = os.getenv("BOT_TESTING_CHANNEL")
PRIVILEGED_ROLES = {'Frequent Thumbers', 'Moderators', 'The Hub'}
COOLDOWN_WHITELIST = {"Moderators", "The Hub"}
PRIV_COUNT = 4
DEV_COUNT = 2
DEFAULT_COOLDOWN = 300
VIP_COOLDOWN = 180
POST_RATE = 1


class SpecialCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.da_rest = DARest()

    @commands.command(name='store-da-name')
    async def store_name(self, ctx, discord_id: discord.Member, username):
        self.da_rest.store_da_name(discord_id.id, username)
        await ctx.send(f"Storing or updating DA username {username} for user {discord_id.display_name}")

    @commands.cooldown(POST_RATE, DEFAULT_COOLDOWN, commands.BucketType.user)
    @commands.command(name='roll')
    async def roll_dice(self, ctx):
        await ctx.send(f"{ctx.message.author.display_name} Rolling 1d20: {random.randint(1, 20)}")


async def setup(bot):
    await bot.add_cog(SpecialCommands(bot))
