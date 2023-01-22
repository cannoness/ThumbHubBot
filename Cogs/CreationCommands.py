from collections import defaultdict

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
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def custom_cooldown(ctx):
        roles = {role.name for role in ctx.author.roles}
        if not COOLDOWN_WHITELIST.isdisjoint(roles):
            return None
        elif not PRIVILEGED_ROLES.isdisjoint(roles):
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
        if results:
            if channel.name == "nsfw-share":
                results = list(filter(lambda image:  image["is_mature"], results))
            elif channel.name != "bot-testing":
                results = list(filter(lambda image: not image["is_mature"], results))

        if not results and username:
            await channel.send(f"Couldn't find any art for {username}! Is their gallery private? "
                               f"Use !lit for literature share")
            ctx.command.reset_cooldown(ctx)
            return
        return results

    @staticmethod
    async def _filter_lit_results(ctx, results, channel, username=None):
        # filter out lit
        if results:
            if channel.name == "nsfw-share":
                results = list(filter(lambda lit:  lit["is_mature"], results))
            elif channel.name != "bot-testing":
                results = list(filter(lambda lit: not lit["is_mature"], results))

        if not results and username:
            await channel.send(f"Couldn't find any literature for {username}! Is their gallery private? "
                               f"Use !art for visual art share")
            ctx.command.reset_cooldown(ctx)
            return
        return results

    async def _send_art_results(self, ctx, channel, results, message, username=None, usernames=None, display_num=None):
        display_count = self._check_your_privilege(ctx)
        display = display_count if (not display_num or display_num >= display_count) else display_num
        if not usernames:
            results = await self._filter_image_results(ctx, results, channel, username)
            if not results:
                return
            ping_user = self.da_rest.fetch_discord_id(username) if username else None
            mention_string = ctx.message.guild.get_member(ping_user).mention if ping_user else None
        else:
            mention_string = []
            for user in usernames:
                ping_user = self.da_rest.fetch_discord_id(user)
                mention_string.append(ctx.message.guild.get_member(ping_user).mention if ping_user else None)
            mention_list = list(filter(lambda mention: mention is not None, mention_string))
            mention_string = ", ".join(mention_list) if len(mention_list) > 0 else None
        embed = []
        for result in results[:display]:
            embed.append(self._build_embed(result['src_image'], message) if not usernames else
                         self._build_embed(result['media_content'][-1]['url'], message))
        await channel.send(mention_string, embeds=embed) if mention_string else await channel.send(embeds=embed)

    async def _send_lit_results(self, ctx, channel, results, username=None, usernames=None, display_num=None):
        display_count = int(self._check_your_privilege(ctx))
        display = display_count if (not display_num or display_num >= display_count) else display_num
        if not usernames:
            # filter out lit
            results = await self._filter_lit_results(ctx, results, channel, username)
            if not results:
                return
            ping_user = self.da_rest.fetch_discord_id(username) if username else None
            mention_string = ctx.message.guild.get_member(ping_user).mention if ping_user else None
        else:
            mention_string = []
            for user in usernames:
                ping_user = self.da_rest.fetch_discord_id(user)
                mention_string.append(ctx.message.guild.get_member(ping_user).mention if ping_user else None)
            mention_list = list(filter(lambda mention: mention is not None, mention_string))
            mention_string = ", ".join(mention_list) if len(mention_list) > 0 else None

        embed = discord.Embed()
        nl = '\n'
        try:
            for result in results[:display]:
                embed.add_field(
                    name=f"{result['title']}: ({result['url']})", value=f"'{result['src_snippet'].replace('<br />', nl)}'",
                    inline=False)
            await channel.send(mention_string, embed=embed) if mention_string else await channel.send(embed=embed)
        except Exception as ex:
            print(ex)

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
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
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
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
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
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def my_art(self, ctx, *args):
        channel = self._set_channel(ctx, [ART_LIT_CHANNEL, NSFW_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return
        username = self.da_rest.fetch_da_username(ctx.message.author.id)
        if not username:
            await ctx.send(f"Username not found in store for user {ctx.message.author.mention}, please add to store u"
                           f"sing !store-da-name `username`")
            ctx.command.reset_cooldown(ctx)
            return
        await self.art(ctx, username, *args, channel=channel)

    @commands.command(name='mylit')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def my_lit(self, ctx, *args):
        channel = self._set_channel(ctx, [ART_LIT_CHANNEL, NSFW_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return
        username = self.da_rest.fetch_da_username(ctx.message.author.id)
        if not username:
            await ctx.send(f"Username not found in store for user {ctx.message.author.mention}, please add to store u"
                           f"sing !store-da-name `username`")
            ctx.command.reset_cooldown(ctx)
            return
        await self.lit(ctx, username, *args, channel=channel)

    @commands.command(name='random')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
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

    def _parse_args(self, *args):
        if len(args) == 0:
            return None
        arg_dict = defaultdict(None)
        if 'random' in args or 'rnd' in args:
            arg_dict['random'] = True
        if args[-1].isdigit():
            arg_dict['show_only'] = int(args[-1])
        if '+' in "\t".join(args):
            arg_dict['offset'] = int(self._get_clean_arg(args, '+'))
        if 'category /' in "\t".join(args):
            arg_dict['category'] = self._get_clean_arg(args, '/')
        if 'gallery "' in "\t".join(args):
            arg_dict['gallery'] = self._get_clean_arg(args, '"')[:-1]
        if '#' in "\t".join(args):
            arg_dict['tags'] = self._get_clean_arg(args, '#')
        if 'old' in args:
            arg_dict['old'] = True
        if 'pop' in args or 'popular' in args:
            arg_dict['pop'] = True
        return arg_dict

    @staticmethod
    def _get_clean_arg(args, string):
        index = [idx for idx, arg in enumerate(args) if string in arg][0]
        return args[index][1:]

    def _fetch_based_on_args(self, username, version, arg):
        offset = arg['offset'] if arg and 'offset' in arg.keys() else 0
        display_num = arg['show_only'] if arg and 'show_only' in arg.keys() else 24
        if arg:
            if 'random' in arg.keys():
                results = self.da_rest.fetch_entire_user_gallery(username, version)
                random.shuffle(results)
                return results, offset, display_num
            elif 'pop' in arg.keys():
                return self.da_rest.fetch_user_popular(username, version, display_num), offset, display_num
            elif 'old' in arg.keys():
                return self.da_rest.fetch_user_old(username, version, display_num), offset, display_num

        return self.da_rest.fetch_user_gallery(username, version, offset, display_num), offset, display_num

    @commands.command(name='art')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def art(self, ctx, username, *args, channel=None):
        try:
            arg = self._parse_args(*args)
            if not channel:
                channel = self._set_channel(ctx, [DISCOVERY_CHANNEL])
                if channel.id is not ctx.message.channel.id:
                    ctx.command.reset_cooldown(ctx)
                    return

            results, offset, display_num = self._fetch_based_on_args(username, "src_image", arg)

            if not results and username and arg and ('pop' in arg.keys() or 'old' in arg.keys()):
                await channel.send(f"{username} must be in store to use 'pop' and 'old'")
                ctx.command.reset_cooldown(ctx)
                return
            message = f"Visit {username}'s gallery: http://www.deviantart.com/{username}"
            await self._send_art_results(ctx, channel, results, message, username=username, display_num=display_num)
        except Exception as ex:
            print(ex)

    @commands.command(name='myfavs')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def my_favs(self, ctx):
        username = self.da_rest.fetch_da_username(ctx.message.author.id)
        if not username:
            await ctx.send(f"Username not found in store for user {ctx.message.author.mention}, please add to store u"
                           f"sing !store-da-name `username`")
            ctx.command.reset_cooldown(ctx)
            return

        channel = self._set_channel(ctx, [DISCOVERY_CHANNEL])
        if channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return
        await self.favs(ctx, username, channel)

    @commands.command(name='favs')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def favs(self, ctx, username, channel=None):
        if not channel:
            channel = self._set_channel(ctx, [DISCOVERY_CHANNEL])
            if channel.id is not ctx.message.channel.id:
                ctx.command.reset_cooldown(ctx)
                return

        await ctx.send(f"Loading favorites for user {username}, this may take a moment...")
        num = self._check_your_privilege(ctx)
        results, users, links, _ = self.da_rest.get_user_favs(username, num)

        if len(results) == 0 and username:
            await channel.send(f"Couldn't find any faves for {username}! Do they have any favorites?")
            ctx.command.reset_cooldown(ctx)
            return
        message = f"A collection of favorites from user {username}, by users {users}: {', '.join(links)}"
        await self._send_art_results(ctx, channel, results, message, usernames=[username])

    @commands.command(name='lit')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def lit(self, ctx, username, *args, channel=None):
        try:
            arg = self._parse_args(*args)
            if not channel:
                channel = self._set_channel(ctx, [DISCOVERY_CHANNEL])
                if channel.id is not ctx.message.channel.id:
                    ctx.command.reset_cooldown(ctx)
                    return

            results, offset, display_num = self._fetch_based_on_args(username, "src_snippet", arg)
            if not results and username and arg and ('pop' in arg.keys() or 'old' in arg.keys()):
                await channel.send(f"{username} must be in store to use 'pop' and 'old'")
                ctx.command.reset_cooldown(ctx)
                return
            await self._send_lit_results(ctx, channel, results, username=username, display_num=display_num)
        except Exception as ex:
            print(ex)

    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
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


async def setup(bot):
    await bot.add_cog(CreationCommands(bot))
