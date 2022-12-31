# bot.py
from Utilities.DA_rest import DARest
import ast
import json
import random
import discord
from discord.ext import commands
import os

import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
ART_LIT_CHANNEL = os.getenv("ART_LIT_CHANNEL")
BOT_TESTING_CHANNEL = os.getenv("BOT_TESTING_CHANNEL")

intent = discord.Intents.all()

da_rest = DARest()

bot = commands.Bot(command_prefix="!", intents=intent)


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.ext.commands.MissingRequiredArgument):
        await ctx.send(r"Something went wrong ¯\_(ツ)_/¯")
        print("command didn't work.")
    if isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
        minutes, seconds= divmod(error.retry_after, 60)
        await ctx.send(f"This command is on cooldown for user {ctx.message.author.display_name}, try again after "
                       f"{int(minutes)}m {int(seconds)}s.")
        print("command didn't work.")


whitelist = {"Moderators", "The Hub"}


def custom_cooldown(ctx):
    roles = {role.name for role in ctx.author.roles}
    if not whitelist.isdisjoint(roles):
        return None
    elif "TheHubVIP" in roles:
        discord.app_commands.Cooldown(1, 180)
    else:
        return discord.app_commands.Cooldown(1, 300)


@bot.command(name='art')
@commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
async def my_art(ctx, username=None, *args):
    channel = bot.get_channel(int(ART_LIT_CHANNEL))

    # added so we don't spam lit share during testing
    if ctx.message.channel.id == int(BOT_TESTING_CHANNEL):
        channel = bot.get_channel(int(BOT_TESTING_CHANNEL))

    if not username:
        await ctx.send("Must specify a user until random is turned on")

    offset = args[0] if 'random' not in args and len(args) > 0 else 0

    if 'random' in args:
        results = da_rest.fetch_entire_user_gallery(username)
        random.shuffle(results)
    else:
        results = da_rest.fetch_user_gallery(username, offset)

    # filter out lit
    results = list(filter(lambda x: x['category'] != 'Literature', results))
    user_roles = [role.name for role in ctx.message.author.roles]
    message = f"Visit {username}'s gallery: http://www.deviantart.com/{username}"
    if not {'Frequent Thumbers', 'Moderators', 'The Hub'}.isdisjoint(set(user_roles)):
        embed = []
        for result in results[:4]:
            embed.append(discord.Embed(url="http://deviantart.com", description=message).set_image(url=result['preview']['src']))
        await channel.send(embeds=embed)

    else:
        embed = []
        for result in results[:2]:
            embed.append(discord.Embed(url="http://deviantart.com", description=message).set_image(url=result['preview']['src']))
        await channel.send(embeds=embed)

    if channel.id is not ctx.message.channel.id:
        await ctx.send(f"{username}'s art has been posted in #art-lit-share!")


@commands.cooldown(1, 300, commands.BucketType.user)
@bot.command(name='roll')
async def roll_dice(ctx):
    await ctx.send(f"{ctx.message.author.display_name} Rolling 1d20: {random.randint(1, 20)}")


@commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
@bot.command(name='dailies')
async def get_dds(ctx):
    channel = bot.get_channel(int(ART_LIT_CHANNEL))

    # added so we don't spam lit share during testing
    if ctx.message.channel.id == int(BOT_TESTING_CHANNEL):
        channel = bot.get_channel(int(BOT_TESTING_CHANNEL))

    results = da_rest.fetch_daily_deviations()
    results = list(filter(lambda x: x['category'] != 'Literature', results))
    random.shuffle(results)
    user_roles = [role.name for role in ctx.message.author.roles]
    if not {'Frequent Thumbers', 'Moderators', 'The Hub'}.isdisjoint(set(user_roles)):
        embed = []
        for result in results[:4]:
            embed.append(discord.Embed(url="http://deviantart.com", description="A Selection from today's Daily Deviations").set_image(
                url=result['preview']['src']))
        await channel.send(embeds=embed)

    else:
        embed = []
        for result in results[:2]:
            embed.append(
                discord.Embed(url="http://deviantart.com", description="test").set_image(url=result['preview']['src']))
        await channel.send(embeds=embed)

    if channel.id is not ctx.message.channel.id:
        await ctx.send("dds have been posted in #art-lit-share!")

bot.run(TOKEN)

