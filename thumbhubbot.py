# bot.py
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
secret = os.getenv("SECRET")
CHANNEL = os.getenv("ART_LIT_CHANNEL")
intent = discord.Intents.all()


def home():
    r = requests.get(f"https://www.deviantart.com/oauth2/token?grant_type=client_credentials&client_id=12390&client_secret={secret}")
    return r.content


def gallery(access_token, username, offset):
    r = requests.get("https://www.deviantart.com/api/v1/oauth2/gallery/all?username="+username+"&limit=24&mature_content=false&access_token="+
                     access_token+"&offset="+offset)
    return r.content


def dds(access_token):
    r = requests.get(f"https://www.deviantart.com/api/v1/oauth2/browse/dailydeviations?access_token={access_token}")
    return r.content


bot = commands.Bot(command_prefix="!", intents=intent)


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.ext.commands.MissingRequiredArgument):
        await ctx.send("Something went wrong ¯\_(ツ)_/¯")
        print("{Fore.RED}command didn't work.")
    if isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
        minutes, seconds= divmod(error.retry_after, 60)
        await ctx.send(f"This command is on cooldown for user {ctx.message.author.display_name}, try again after "
                       f"{int(minutes)}m {int(seconds)}s.")
        print("{Fore.RED}command didn't work.")


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
async def my_art(ctx, arg1=None, *args):
    channel = bot.get_channel(CHANNEL)
    if not arg1:
        await ctx.send("must specify a user until random is turned on")
    if 'random' in args:
        arg2 = random.randint(0, 10)
    elif len(args):
        arg2 = args[0]
    else:
        arg2 = 0

    test = home()
    dict_str = test.decode("UTF-8")
    mydata = ast.literal_eval(dict_str)
    response = gallery(access_token=mydata['access_token'], username=arg1, offset=str(arg2))
    dict_str = response.decode("UTF-8")
    test = json.loads(dict_str)
    results = test['results']
    if 'random' in args:
        random.shuffle(results)
    user_roles = [role.name for role in ctx.message.author.roles]
    message = f"Visit {arg1}'s gallery: http://www.deviantart.com/{arg1}"
    if not {'Frequent Thumbers', 'Moderators', 'The Hub'}.isdisjoint(set(user_roles)):
        embed = []
        for result in results[:4]:
            if result['category'] != 'Literature':
                embed.append(discord.Embed(url="http://deviantart.com", description=message).set_image(url=result['preview']['src']))
        await channel.send(embeds=embed)

    else:
        embed = []
        for result in test['results'][:2]:
            embed.append(discord.Embed(url="http://deviantart.com", description=message).set_image(url=result['preview']['src']))
        await channel.send(embeds=embed)

    if channel.id is not ctx.message.channel.id:
        await ctx.send(f"{arg1}'s art has been posted in #art-lit-share!")


@commands.cooldown(1, 300, commands.BucketType.user)
@bot.command(name='roll')
async def roll_dice(ctx):
    await ctx.send(f"{ctx.message.author.display_name} Rolling 1d20: {random.randint(1, 20)}")


@commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
@bot.command(name='dailies')
async def get_dds(ctx):
    channel = bot.get_channel(712405430487482389)
    test = home()
    dict_str = test.decode("UTF-8")
    mydata = ast.literal_eval(dict_str)
    response = dds(access_token=mydata['access_token'])
    dict_str = response.decode("UTF-8")
    test = json.loads(dict_str)
    results = test['results']
    random.shuffle(results)
    user_roles = [role.name for role in ctx.message.author.roles]
    if not {'Frequent Thumbers', 'Moderators', 'The Hub'}.isdisjoint(set(user_roles)):
        embed = []
        for result in results[:4]:
            if result['category'] != 'Literature':
                embed.append(discord.Embed(url="http://deviantart.com", description="A Selection from today's Daily Deviations").set_image(
                    url=result['preview']['src']))
        await channel.send(embeds=embed)

    else:
        embed = []
        for result in test['results'][:2]:
            embed.append(
                discord.Embed(url="http://deviantart.com", description="test").set_image(url=result['preview']['src']))
        await channel.send(embeds=embed)

    if channel.id is not ctx.message.channel.id:
        await ctx.send("dds have been posted in #art-lit-share!")

bot.run(TOKEN)

