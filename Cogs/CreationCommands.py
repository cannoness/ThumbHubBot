import os
import random
import re
from collections import defaultdict
from io import BytesIO

import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv

from Utilities.DARest import DARest
from Utilities.DARSS import DARSS
from Utilities.DatabaseActions import DatabaseActions
from Utilities.ImageUtils import Template

load_dotenv()
MOD_CHANNEL = os.getenv("MOD_CHANNEL")
NSFW_CHANNEL = os.getenv("NSFW_CHANNEL")
BOT_TESTING_CHANNEL = os.getenv("BOT_TESTING_CHANNEL")
THUMBHUB_CHANNEL = os.getenv("THUMBHUB_CHANNEL")
PRIVILEGED_ROLES = {'Frequent Thumbers'}
VIP = "The Hub VIP"
COOLDOWN_WHITELIST = {"Moderators", "The Hub", "Bot Sleuth"}
MOD_COUNT = 6
PRIV_COUNT = 6
DEV_COUNT = 4
DEFAULT_COOLDOWN = 1800
PRIV_COOLDOWN = 900
VIP_COOLDOWN = 600
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
            discord.app_commands.Cooldown(POST_RATE, PRIV_COOLDOWN)
        elif VIP in roles:
            discord.app_commands.Cooldown(POST_RATE, VIP_COOLDOWN)
        else:
            return discord.app_commands.Cooldown(POST_RATE, DEFAULT_COOLDOWN)


class CreationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.da_rest = DARest()
        self.db_actions = DatabaseActions()
        self.da_rss = DARSS()

    @staticmethod
    def _check_your_privilege(ctx):
        user_roles = [role.name for role in ctx.message.author.roles]
        privileged = not PRIVILEGED_ROLES.isdisjoint(set(user_roles))
        mod_or_admin = not COOLDOWN_WHITELIST.isdisjoint(set(user_roles))
        return PRIV_COUNT if privileged else MOD_COUNT if mod_or_admin else DEV_COUNT

    def _set_channel(self, ctx, requested_channel):
        # added so we don't spam share during testing
        if str(ctx.message.channel.id) in requested_channel:
            channel = ctx.message.channel
        elif ctx.message.channel.id == int(BOT_TESTING_CHANNEL):
            channel = self.bot.get_channel(int(BOT_TESTING_CHANNEL))
        else:
            channel = None

        if not channel or channel.id is not ctx.message.channel.id:
            ctx.command.reset_cooldown(ctx)
            return

        return channel

    @staticmethod
    async def _filter_results(ctx, results, channel, username=None):
        filtered_results = None
        if results:
            if channel.name == "nsfw":
                filtered_results = list(filter(lambda result: result["is_mature"], results))
                if not filtered_results or len(filtered_results) < 4:  # always return something.
                    sorted_nsfw = sorted(results, key=lambda result: result["is_mature"], reverse=True)
                    return sorted_nsfw
            elif channel.name != "bot-testing":
                filtered_results = list(filter(lambda result: not result["is_mature"], results))
            elif channel.name == "bot-testing":
                filtered_results = list(filter(lambda result: result, results))

        if not (results or filtered_results) and username:
            await channel.send(f"""Couldn't find any deviations for {username}! 
                                    Is their gallery private?""")
            ctx.command.reset_cooldown(ctx)
            return None
        return filtered_results

    def _manage_mentions(self, ctx, username, usernames):
        if not usernames:
            ping_user = self.db_actions.fetch_discord_id(username) if username else None
            return ctx.message.guild.get_member(ping_user).mention if ping_user else username
        else:
            mention_string = []
            for user in usernames:
                username = re.findall(r"{[^]]*\}", user)[0][1:-1]
                ping_user = self.db_actions.fetch_discord_id(username)
                discord_user = ctx.message.guild.get_member(ping_user)
                if discord_user is not None:
                    mention_string.append(re.sub(r"{[^]]*\}", lambda x: x.group(0).replace(f"{{{username}}}",
                                                                                           discord_user.mention),
                                                 user) if discord_user is not None else mention_string.append(
                        re.sub(r"{[^]]*\}", lambda x: x.group(0).replace(f"{{{username}}}",
                                                                         username), user)))
                else:
                    mention_string.append(
                        re.sub(r"{[^]]*\}", lambda x: x.group(0).replace(f"{{{username}}}", username), user))
            return ", ".join(mention_string)

    async def _send_art_results(self, ctx, channel, in_results, message, username=None, usernames=None,
                                display_num=None):
        display_count = self._check_your_privilege(ctx)
        display = display_count if (not display_num or display_num >= display_count) else display_num

        results = await self._filter_results(ctx, in_results, channel, username) if not usernames \
            else in_results
        if not results:
            return

        mention_string = self._manage_mentions(ctx, username, usernames)
        if not usernames:
            final_message = message.format(mention_string)
        else:
            final_message = mention_string

        embeds = []
        titles = []
        for result in results[:display]:
            embeds.append(BytesIO(requests.get(result['src_image']).content) if ('src_image' in result.keys() and
                                                                                 result['src_image'] != "None") else
                          result if 'src_snippet' in result.keys() else
                          BytesIO(requests.get(result['media_content'][-1]['url']).content))
            titles.append(result['title'])
        amaztemp = Template(titles, embeds)
        thumbs = amaztemp.draw()
        with BytesIO() as image_binary:
            thumbs.save(image_binary, 'PNG')
            image_binary.seek(0)
            await channel.send(final_message, file=discord.File(image_binary, filename='thumbs.png'))
        self.db_actions.add_coins(ctx.message.author.id, username)

    @staticmethod
    def _build_embed(url, message, src):
        return discord.Embed(url=f"http://{src}.com", description=message).set_image(url=url)

    async def _check_store(self, ctx):
        username = self.db_actions.fetch_da_username(ctx.message.author.id)
        if not username:
            await ctx.send(f"Username not found in store for user {ctx.message.author.mention}, please add to store u"
                           f"sing !store-da-name `username`")
            ctx.command.reset_cooldown(ctx)
            return
        return username

    @commands.command(name='topic')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def topics(self, ctx, topic, offset=0):
        channel = self._set_channel(ctx, [THUMBHUB_CHANNEL, NSFW_CHANNEL])
        if not channel:
            return
        try:
            results = self.da_rest.get_topic(topic, offset)
            if results[0] is None:
                results = results[1]

            filtered_results = await self._filter_results(ctx, results, channel)
            if not filtered_results:
                await channel.send(f"Couldn't find a topic named {topic}")
                return
            result_string = [f"[[{index + 1}]({image['url']})] {image['author']}" for index, image in
                             enumerate(results[:self._check_your_privilege(ctx)])]
            message = f'''Here are some results for {topic.title()}:
{", ".join(result_string)}'''
            await self._send_art_results(ctx, channel, filtered_results, message,
                                         username=ctx.message.author.display_name)

        except Exception as ex:
            print(ex, flush=True)
            await channel.send(f"Something went wrong! {ex}")

            if channel.name == "bot-testing":
                raise Exception(ex)

    @commands.command(name='myart')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def my_art(self, ctx, *args):
        channel = self._set_channel(ctx, [THUMBHUB_CHANNEL, NSFW_CHANNEL])
        if not channel:
            return
        username = await self._check_store(ctx)
        await self.art(ctx, username, *args, channel=channel)

    @commands.command(name='mylit')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def my_lit(self, ctx, *args):
        channel = self._set_channel(ctx, [THUMBHUB_CHANNEL, NSFW_CHANNEL])
        if not channel:
            return
        username = await self._check_store(ctx)
        await self.lit(ctx, username, *args, channel=channel)

    @commands.command(name='rank')
    async def rank(self, ctx):
        pass

    @commands.command(name='levels')
    async def levels(self, ctx):
        pass

    @commands.command(name='find')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def find_tags_like(self, ctx):
        channel = self._set_channel(ctx, [THUMBHUB_CHANNEL, NSFW_CHANNEL])
        if not channel:
            return
        try:
            # results = self.da_rest.get_topic(topic, offset)
            await channel.send("Coming soon!")
        except Exception as ex:
            print(f"{ex} not implemented", flush=True)

    @commands.command(name='popular')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def popular(self, ctx):
        channel = self._set_channel(ctx, [THUMBHUB_CHANNEL, NSFW_CHANNEL])
        if not channel:
            return
        try:
            # results = self.da_rest.get_topic(topic, offset)
            await channel.send("Coming soon!")
        except Exception as ex:
            print(f"{ex} not implemented", flush=True)

    @commands.command(name='new')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def new(self, ctx):
        channel = self._set_channel(ctx, [THUMBHUB_CHANNEL, NSFW_CHANNEL])
        if not channel:
            return
        try:
            # results = self.da_rest.get_topic(topic, offset)
            await channel.send("Coming soon!")
        except Exception as ex:
            print(f"{ex} not implemented", flush=True)

    @commands.command(name='hot')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def hot(self, ctx):
        channel = self._set_channel(ctx, [THUMBHUB_CHANNEL, NSFW_CHANNEL])
        if not channel:
            return
        try:
            # results = self.da_rest.get_topic(topic, offset)
            await channel.send("Coming soon!")
        except Exception as ex:
            print(f"{ex} not implemented", flush=True)

    @commands.command(name='random')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def random(self, ctx):
        channel = self._set_channel(ctx, [THUMBHUB_CHANNEL, NSFW_CHANNEL])
        try:
            display_count = self._check_your_privilege(ctx)
            results, links = self.da_rss.get_random_images(display_count)
            message = f"{links}"
            usernames = [each for each in links.split(", ")]

            await self._send_art_results(ctx, channel, results, message, usernames=usernames)
        except Exception as ex:
            print(ex, flush=True)
            await channel.send(f"An exception has been recorded, we are displaying a random user.")
            if channel.name == "bot-testing":
                raise Exception(ex)
            await self.art(ctx, self.db_actions.fetch_da_usernames(1)[0], 'rnd', channel=channel)

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
        if 'gallery' in "\t".join(args):
            arg_dict['gallery'] = args[args.index("gallery") + 1].lower()
        if '#' in "\t".join(args):
            arg_dict['tags'] = self._get_clean_arg(args, '#')
        if 'old' in args:
            arg_dict['old'] = True
        if 'pop' in args or 'popular' in args:
            arg_dict['pop'] = True
        if 'collection' in "\t".join(args):
            arg_dict['collection'] = args[args.index("collection") + 1]
        return arg_dict

    @staticmethod
    def _get_clean_arg(args, string):
        index = [idx for idx, arg in enumerate(args) if string in arg][0]
        return args[index][1:]

    def _fetch_based_on_args(self, username, arg, max_num):
        offset = arg['offset'] if arg and 'offset' in arg.keys() else 0
        display_num = arg['show_only'] if arg and 'show_only' in arg.keys() else 24
        if arg:
            wants_random = 'random' in arg.keys()
            if 'pop' in arg.keys():
                pop = self.da_rest.fetch_user_popular(username, offset, display_num)
                if not wants_random:
                    return pop, offset, display_num
                random.shuffle(pop)
                return pop, offset, display_num
            elif 'old' in arg.keys():
                old = self.da_rest.fetch_user_old(username, offset, display_num)
                if not wants_random:
                    return old, offset, display_num
                random.shuffle(old)
                return old, offset, display_num
            elif 'gallery' in arg.keys():
                gallery = self.da_rest.get_user_gallery(username, arg['gallery'], offset, display_num)
                if not wants_random:
                    return gallery, offset, display_num
                random.shuffle(gallery)
                return gallery, offset, display_num
            elif 'tags' in arg.keys():
                with_tags = self.da_rest.get_user_devs_by_tag(username, arg['tags'], offset, display_num)
                if not wants_random:
                    return with_tags, offset, display_num
                random.shuffle(with_tags)
                return with_tags, offset, display_num
            elif wants_random:
                results = self.da_rest.fetch_entire_user_gallery(username)
                random.shuffle(results)
                return results, offset, display_num

        return self.da_rest.fetch_user_gallery(username, offset, display_num), offset, display_num

    @commands.command(name='why')
    async def why_easter_egg(self, ctx):
        await ctx.send("42")

    @commands.command(name='art')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def art(self, ctx, username, *args, channel=None):
        try:
            arg = self._parse_args(*args)
            if not channel:
                channel = self._set_channel(ctx, [THUMBHUB_CHANNEL, NSFW_CHANNEL])

            results, offset, display_num = self._fetch_based_on_args(username, arg,
                                                                     self._check_your_privilege(ctx))

            if not results and username and arg and ('pop' in arg.keys() or 'old' in arg.keys()):
                await channel.send(f"{username} must be in store to use 'pop' and 'old'")
                ctx.command.reset_cooldown(ctx)
                return
            filtered_results = await self._filter_results(ctx, results, channel, username)
            if not filtered_results:
                await channel.send("No results found in that gallery, please try again.")
                ctx.command.reset_cooldown(ctx)
                return
            thumbs = ", ".join(list(f"[{index + 1}]({image['url']})" for index, image in
                                    enumerate(filtered_results[:self._check_your_privilege(ctx)])))
            message = f'''Visit {{}}'s [gallery](http://www.deviantart.com/{username})! [{thumbs}]'''

            await self._send_art_results(ctx, channel, filtered_results, message, username=username,
                                         display_num=display_num)
        except Exception as ex:
            print(ex, flush=True)
            await channel.send(f"Encountered exception {ex}. This has been recorded.")
            if channel.name == "bot-testing":
                raise Exception(ex)

    @commands.command(name='myfavs')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def my_favs(self, ctx, *args):
        username = await self._check_store(ctx)
        channel = self._set_channel(ctx, [THUMBHUB_CHANNEL])
        await self.favs(ctx, username, *args, channel=channel)

    @commands.command(name='favs')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def favs(self, ctx, username, *args, channel=None):
        if not channel:
            channel = self._set_channel(ctx, [THUMBHUB_CHANNEL])

        arg = self._parse_args(*args)
        priv_count = self._check_your_privilege(ctx)
        display_num = arg['show_only'] if arg and 'show_only' in arg.keys() and arg['show_only'] <= priv_count else \
            priv_count
        rnd = True if arg and 'random' in arg.keys() else False
        offset = arg['offset'] if arg and 'offset' in arg.keys() else 0

        try:
            if arg and 'collection' in arg.keys():
                results, links = self.da_rest.get_user_favs_by_collection(username, arg['collection'], offset,
                                                                          display_num)
            else:
                results, links = self.da_rss.get_user_favs(username, offset, display_num, rnd)

            if len(results) == 0 and username:
                await channel.send(f"Couldn't find any faves for {username}! Do they have any favorites?")
                ctx.command.reset_cooldown(ctx)
                return
            message = f"{links}"
            usernames = [each for each in links.split(", ")]
            await self._send_art_results(ctx, channel, results, message, usernames=usernames)
        except Exception as ex:
            print(ex, flush=True)
            await channel.send(f"An exception has been recorded, we are displaying a random user.")
            if channel.name == "bot-testing":
                raise Exception(ex)
            await self.art(ctx, self.db_actions.fetch_da_usernames(1)[0], 'rnd', channel=channel)

    @commands.command(name='lit')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def lit(self, ctx, username, *args, channel=None):
        try:
            arg = self._parse_args(*args)
            if not channel:
                channel = self._set_channel(ctx, [THUMBHUB_CHANNEL, NSFW_CHANNEL])

            results, offset, display_num = self._fetch_based_on_args(username, arg, self._check_your_privilege(ctx))
            if not results and username and arg and ('pop' in arg.keys() or 'old' in arg.keys()):
                await channel.send(f"{username} must be in store to use 'pop' and 'old'")
                ctx.command.reset_cooldown(ctx)
                return
            await self._send_art_results(ctx, channel, results, message="", username=username, display_num=display_num)
        except Exception as ex:
            print(ex, flush=True)
            await channel.send(f"Something went wrong! {ex}")
            if channel.name == "bot-testing":
                raise Exception(ex)

    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    @commands.command(name='dailies')
    async def get_dds(self, ctx):
        channel = self._set_channel(ctx, [THUMBHUB_CHANNEL])
        try:
            results = self.da_rest.fetch_daily_deviations()
            filtered_results = await self._filter_results(ctx, results, channel)
            if not filtered_results:
                await channel.send(f"Couldn't fetch dailies, try again.")
                return
            # shuffle is breaking somehow.
            # random.shuffle(filtered_results)
            result_string = [f"[[{index + 1}]({image['url']})] {image['author']}" for index, image in
                             enumerate(results[:self._check_your_privilege(ctx)])]
            message = f'''From today's [Daily Deviations](https://www.deviantart.com/daily-deviations): 
{", ".join(result_string)}'''
            await self._send_art_results(ctx, channel, filtered_results, message,
                                         username=ctx.message.author.display_name)
        except Exception as ex:
            print(ex, flush=True)
            await channel.send(f"Something went wrong! {ex}")

            if channel.name == "bot-testing":
                raise Exception(ex)


async def setup(bot):
    await bot.add_cog(CreationCommands(bot))
