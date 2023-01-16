from Utilities.DA_rest import DARest
from Utilities.IG_rest import IGRest
from Utilities.Twitter_rest import TwitterRest
from discord.ext import commands
import discord
import os
import random

from dotenv import load_dotenv

load_dotenv()
ART_LIT_CHANNEL = os.getenv("ART_LIT_CHANNEL")
NSFW_CHANNEL = os.getenv("NSFW_CHANNEL")
BOT_TESTING_CHANNEL = os.getenv("BOT_TESTING_CHANNEL")
DISCOVERY_CHANNEL = os.getenv("DISCOVERY_CHANNEL")
PRIVILEGED_ROLES = {'Frequent Thumbers', "TheHubVIP"}
COOLDOWN_WHITELIST = {"Moderators", "The Hub"}
MOD_COUNT = 4
PRIV_COUNT = 4
DEV_COUNT = 2
DEFAULT_COOLDOWN = 600
VIP_COOLDOWN = 300
POST_RATE = 1


class Private:
    @staticmethod
    def _custom_cooldown(ctx):
        roles = {role.name for role in ctx.author.roles}
        if not COOLDOWN_WHITELIST.isdisjoint(roles):
            return None
        elif PRIVILEGED_ROLES.isdisjoint(roles):
            discord.app_commands.Cooldown(POST_RATE, VIP_COOLDOWN)
        else:
            return discord.app_commands.Cooldown(POST_RATE, DEFAULT_COOLDOWN)


class CreationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.da_rest = DARest()
        self.ig_rest = IGRest()
        self.twitter_rest = TwitterRest()

    @staticmethod
    def _check_your_privilege(ctx):
        user_roles = [role.name for role in ctx.message.author.roles]
        privileged = not PRIVILEGED_ROLES.isdisjoint(set(user_roles))
        mod_or_admin = not COOLDOWN_WHITELIST.isdisjoint(set(user_roles))
        return PRIV_COUNT if privileged else MOD_COUNT if mod_or_admin else DEV_COUNT

    def _set_channel(self, ctx, channel):
        # added so we don't spam share during testing
        if str(ctx.message.channel.id) in channel:
            return ctx.message.channel
        elif ctx.message.channel.id == int(BOT_TESTING_CHANNEL):
            return self.bot.get_channel(int(BOT_TESTING_CHANNEL))
        return None

    @staticmethod
    async def _filter_image_results(ctx, results, channel, username=None):
        # filter out lit
        if channel.name == "nsfw-share":
            results = list(filter(lambda image: 'preview' in image.keys() and image["is_mature"], results))
        else:
            results = list(filter(lambda image: 'preview' in image.keys() and not image["is_mature"], results))

        if len(results) == 0 and username:
            await channel.send(f"Couldn't find any art for {username}! Is their gallery private? "
                               f"Use !lit for literature share")
            ctx.command.reset_cooldown(ctx)
            return
        return results

    @staticmethod
    async def _filter_lit_results(ctx, results, channel, username=None):
        # filter out lit
        if channel.name == "nsfw-share":
            results = list(filter(lambda lit: 'preview' not in lit.keys() and lit["is_mature"], results))
        else:
            results = list(filter(lambda lit: 'preview' not in lit.keys() and not lit["is_mature"], results))

        if len(results) == 0 and username:
            await channel.send(f"Couldn't find any literature for {username}! Is their gallery private? "
                               f"Use !art for visual art share")
            ctx.command.reset_cooldown(ctx)
            return
        return results

    async def _send_art_results(self, ctx, channel, results, message, username=None, usernames=None):
        display_count = self._check_your_privilege(ctx)
        if not usernames:
            results = await self._filter_image_results(ctx, results, channel, username)
            ping_user = self.da_rest.fetch_discord_id(username) if username else None
            mention_string = ctx.message.guild.get_member(ping_user).mention if ping_user else None
        else:
            mention_string = []
            for user in usernames:
                ping_user = self.da_rest.fetch_discord_id(user)
                mention_string.append(ctx.message.guild.get_member(ping_user).mention if ping_user else None)
            mention_string = ", ".join(mention_string)
        embed = []
        for result in results[:display_count]:
            embed.append(self._build_embed(result['preview']['src'], message) if not usernames else \
                         self._build_embed(result['media_content'][-1]['url'], message))
        await channel.send(mention_string, embeds=embed) if mention_string else await channel.send(embeds=embed)

    @staticmethod
    def _build_embed(url, message):
        return discord.Embed(url="http://deviantart.com", description=message).set_image(url=url)

    @commands.command(name='nomention')
    async def do_not_mention(self, ctx, user: discord.Member):
        self.da_rest.do_not_ping_me(user.id)
        await ctx.channel.send(f"We will no longer mention you {user.display_name}")

    @commands.command(name='mention')
    async def mention(self, ctx, user: discord.Member):
        self.da_rest.ping_me(user.id)
        await ctx.channel.send(f"We will now mention you {user.display_name}")

    @commands.command(name='twitterart')
    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    async def twitter_art(self, ctx, username, *args):
        channel = self._set_channel(ctx, [DISCOVERY_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return
        display_count = self._check_your_privilege(ctx)
        urls = self.twitter_rest.get_twitter_media(username, display_count)
        if not urls:
            await ctx.send(f"We couldn't find any media for twitter user {username}.")
            ctx.command.reset_cooldown(ctx)
            return
        message = f"A collection of images from twitter user {username}!"
        embed = []
        for url in urls:
            embed.append(
                discord.Embed(url="http://twitter.com", description=message).set_image(url=url))
        await channel.send(embeds=embed)

    @commands.command(name='igart')
    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    async def ig_art(self, ctx, username, *args):
        channel = self._set_channel(ctx, [DISCOVERY_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return
        display_count = self._check_your_privilege(ctx)
        urls = self.ig_rest.get_recent(username, display_count)
        if not urls:
            await ctx.send(f"We couldn't find any posts for IG user {username}.")
            ctx.command.reset_cooldown(ctx)
            return
        message = f"A collection of images from IG user {username}!"
        embed = []
        for url in urls:
            embed.append(
                discord.Embed(url="http://instagram.com", description=message).set_image(url=url))
        await channel.send(embeds=embed)

    @commands.command(name='myart')
    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    async def my_art(self, ctx, *args):
        channel = self._set_channel(ctx, [ART_LIT_CHANNEL, NSFW_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return
        username = self.da_rest.fetch_da_username(ctx.message.author.id)
        if not username:
            await ctx.send(f"Username not found in store for user {ctx.message.author.mention}, please add to store u"
                           f"sing !store-da-name `@yourself` `username`")
            ctx.command.reset_cooldown(ctx)
            return
        await self.art(ctx, username, channel, *args)

    @commands.command(name='mylit')
    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    async def my_lit(self, ctx, *args):
        channel = self._set_channel(ctx, [ART_LIT_CHANNEL, NSFW_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return
        username = self.da_rest.fetch_da_username(ctx.message.author.id)
        if not username:
            await ctx.send(f"Username not found in store for user {ctx.message.author.mention}, please add to store u"
                           f"sing !store-da-name `@yourself` `username`")
            ctx.command.reset_cooldown(ctx)
            return
        await self.lit(ctx, username, channel, *args)

    @commands.command(name='random')
    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    async def random(self, ctx):
        channel = self._set_channel(ctx, [DISCOVERY_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return

        display_count = self._check_your_privilege(ctx)
        await ctx.send("Pulling random images, this may take a moment...")
        results, users, links, usernames = self.da_rest.get_random_images(display_count)
        message = f"A collection of random images from user(s) {users}, {', '.join(links)}!"
        await self._send_art_results(ctx, channel, results, message, usernames=usernames)

    @commands.command(name='art')
    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    async def art(self, ctx, username, channel=None, *args):
        if not channel:
            channel = self._set_channel(ctx, [DISCOVERY_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return

        if 'random' in args:
            results = self.da_rest.fetch_entire_user_gallery(username)
            random.shuffle(results)
        else:
            offset = args[0] if 'random' not in args and len(args) > 0 else 0
            results = self.da_rest.fetch_user_gallery(username, offset)
        message = f"Visit {username}'s gallery: http://www.deviantart.com/{username}"
        await self._send_art_results(ctx, channel, results, message, username)

    @commands.command(name='myfavs')
    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    async def my_favs(self, ctx):
        channel = self._set_channel(ctx, [ART_LIT_CHANNEL, NSFW_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return
        username = self.da_rest.fetch_da_username(ctx.message.author.id)
        if not username:
            await ctx.send(f"Username not found in store for user {ctx.message.author.mention}, please add to store u"
                           f"sing !store-da-name `@yourself` `username`")
            ctx.command.reset_cooldown(ctx)
            return
        await self.favs(ctx, username, channel)

    @commands.command(name='favs')
    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    async def favs(self, ctx, username, channel=None):
        if not channel:
            channel = self._set_channel(ctx, [DISCOVERY_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return

        await ctx.send(f"Loading favorites for user {username}, this may take a moment...")

        results = self.da_rest.get_user_favs(username)

        random.shuffle(results)
        results = self._filter_rss_image_results(results[:10])

        if len(results) == 0 and username:
            await channel.send(f"Couldn't find any faves for {username}! Do they have any favorites?")
            ctx.command.reset_cooldown(ctx)
            return
        message = f"Visit {username}'s favorites at http://www.deviantart.com/{username}/favorites/all"
        await self._send_art_results(ctx, channel, results, message, usernames=[username])

    @commands.command(name='lit')
    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    async def lit(self, ctx, username, channel=None, *args):
        channel = self._set_channel(ctx, [DISCOVERY_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return

        offset = args[0] if 'random' not in args and len(args) > 0 else 0

        if 'random' in args:
            results = self.da_rest.fetch_entire_user_gallery(username)
            random.shuffle(results)
        else:
            results = self.da_rest.fetch_user_gallery(username, offset)

        # filter out lit
        results = await self._filter_lit_results(ctx, results, channel, username)

        display_count = int(self._check_your_privilege(ctx))

        ping_user = self.da_rest.fetch_discord_id(username) if username else None
        mention_string = ctx.message.guild.get_member(ping_user).mention if ping_user else None
        embed = discord.Embed()
        for result in results[:display_count]:
            embed.add_field(
                name=f"{result['title']}: ({result['url']})", value=result['text_content']['excerpt'][:1024],
                inline=False)
        await channel.send(mention_string, embed=embed) if mention_string else await channel.send(embed=embed)

    @commands.dynamic_cooldown(Private._custom_cooldown, type=commands.BucketType.user)
    @commands.command(name='dailies')
    async def get_dds(self, ctx):
        channel = self._set_channel(ctx, [DISCOVERY_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return

        results = self.da_rest.fetch_daily_deviations()
        results = await self._filter_image_results(ctx, results, channel)
        random.shuffle(results)
        message = "A Selection from today's Daily Deviations"
        await self._send_art_results(ctx, channel, results, message)

    @staticmethod
    def _filter_rss_image_results(results):
        return list(filter(lambda image: 'media_content' in image.keys() and image["rating"] == 'nonadult',
                           results))


async def setup(bot):
    await bot.add_cog(CreationCommands(bot))
