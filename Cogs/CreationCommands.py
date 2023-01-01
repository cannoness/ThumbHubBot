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


class Private:
    @staticmethod
    def _custom_cooldown(ctx):
        roles = {role.name for role in ctx.author.roles}
        if not COOLDOWN_WHITELIST.isdisjoint(roles):
            return None
        elif "TheHubVIP" in roles:
            discord.app_commands.Cooldown(POST_RATE, VIP_COOLDOWN)
        else:
            return discord.app_commands.Cooldown(POST_RATE, DEFAULT_COOLDOWN)


class CreationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.da_rest = DARest()

    @staticmethod
    def _check_your_privilege(ctx):
        user_roles = [role.name for role in ctx.message.author.roles]
        privileged = not PRIVILEGED_ROLES.isdisjoint(set(user_roles))
        return PRIV_COUNT if privileged else DEV_COUNT

    def _set_channel(self, ctx):
        channel = self.bot.get_channel(int(ART_LIT_CHANNEL))

        # added so we don't spam lit share during testing
        if ctx.message.channel.id == int(BOT_TESTING_CHANNEL):
            channel = self.bot.get_channel(int(BOT_TESTING_CHANNEL))
        return channel

    @commands.command(name='art')
    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    async def my_art(self, ctx, username=None, *args):
        channel = self._set_channel(ctx)

        display_count = self._check_your_privilege(ctx)
        if not username or username == 'random' or isinstance(username, int):
            await ctx.send("Pulling random images, this may take a moment...")
            results, users = self.da_rest.get_random_images(display_count)
        elif 'random' in args:
            results = self.da_rest.fetch_entire_user_gallery(username)
            random.shuffle(results)
        else:
            offset = args[0] if 'random' not in args and len(args) > 0 else 0
            results = self.da_rest.fetch_user_gallery(username, offset)

        # filter out lit
        results = list(filter(lambda image: 'preview' in image.keys(), results))
        if len(results) == 0 and username:
            await channel.send(f"Couldn't find any art for {username}! Is their gallery private? "
                               f"Use !lit for literature share")
            return
        message = f"Visit {username}'s gallery: http://www.deviantart.com/{username}"
        if not username:
            message = f"Displaying random images by {', '.join(users)}!"
        embed = []
        for result in results[:display_count]:
            embed.append(discord.Embed(url="http://deviantart.com", description=message).set_image(url=result['preview']['src']))
        await channel.send(embeds=embed)

        if channel.id is not ctx.message.channel.id:
            if username:
                await ctx.message.channel.send(f"{username}'s art has been posted in #art-lit-share!")
            else:
                await ctx.message.channel.send("Random art has been posted in #art-lit-share!")

    @commands.command(name='favs')
    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    async def my_favs(self, ctx, username):
        channel = self._set_channel(ctx)

        await ctx.send(f"Loading favorites for user {username}, this may take a moment...")

        results = self.da_rest.get_user_favs(username)

        # filter out lit
        results = list(filter(lambda image: 'preview' in image.keys(), results))
        random.shuffle(results)

        if len(results) == 0 and username:
            await channel.send(f"Couldn't find any faves for {username}! Do they have any favorites?")
            return
        message = f"Visit {username}'s favorites: http://www.deviantart.com/{username}/favorites"
        display_count = self._check_your_privilege(ctx)
        embed = []
        for result in results[:display_count]:
            embed.append(discord.Embed(url="http://deviantart.com", description=message).set_image(url=result['preview']['src']))
        await channel.send(embeds=embed)

        if channel.id is not ctx.message.channel.id:
            await ctx.send(f"{username}'s favorites have been posted in #art-lit-share!")

    @commands.command(name='lit')
    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    async def my_lit(self, ctx, username, *args):
        channel = self._set_channel(ctx)

        offset = args[0] if 'random' not in args and len(args) > 0 else 0

        if 'random' in args:
            results = self.da_rest.fetch_entire_user_gallery(username)
            random.shuffle(results)
        else:
            results = self.da_rest.fetch_user_gallery(username, offset)

        # filter out lit
        results = list(filter(lambda lit: 'preview' not in lit.keys(), results))
        if len(results) == 0:
            await ctx.message.channel.send(f"Couldn't find any literature for {username}! Is their gallery private? "
                                           f"Use !art for visual art share")
            return
        message = f"Visit {username}'s gallery: http://www.deviantart.com/{username}"

        display_count = int(self._check_your_privilege(ctx)/2)

        for result in results[:display_count]:
            embed = discord.Embed(url="http://deviantart.com", description=message).add_field(
                name=result['title'], value=result['text_content']['excerpt'][:1024])
            await channel.send(embed=embed)

        if channel.id is not ctx.message.channel.id:
            await ctx.send(f"{username}'s literature has been posted in #art-lit-share!")

    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    @commands.command(name='dailies')
    async def get_dds(self, ctx):
        channel = self._set_channel(ctx)

        results = self.da_rest.fetch_daily_deviations()
        results = list(filter(lambda image: 'preview' in image.keys(), results))
        random.shuffle(results)
        display_count = self._check_your_privilege(ctx)
        embed = []
        for result in results[:display_count]:
            embed.append(discord.Embed(url="http://deviantart.com", description="A Selection from today's Daily Deviations").set_image(
                url=result['preview']['src']))
        await channel.send(embeds=embed)

        if channel.id is not ctx.message.channel.id:
            await ctx.send("dds have been posted in #art-lit-share!")


async def setup(bot):
    await bot.add_cog(CreationCommands(bot))
