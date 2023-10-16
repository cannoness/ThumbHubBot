import os
import random
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
COOLDOWN_WHITELIST = {"Moderators", "The Hub",  "Bot Sleuth"}
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
    async def _filter_results(ctx, results, channel, result_type, username=None):
        if results:
            if channel.name == "nsfw-share":
                results = list(filter(lambda result: result["is_mature"] and result[result_type] not in [None, "None"],
                                      results))
            elif channel.name != "bot-testing":
                results = list(filter(lambda result: not result["is_mature"] and result[result_type] not in
                                      [None, "None"], results))
            elif channel.name == "bot-testing":
                results = list(filter(lambda result: result[result_type] not in [None, "None"],
                                      results))

        if not results and username:
            await channel.send(f"""Couldn't find any {"art" if 'src_image' in result_type else "lit"} for {username}! 
                                Is their gallery private? 
                               {"Use !art for image share" if 'src_snippet' in result_type else
            "Use !lit for literature share"}""")
            ctx.command.reset_cooldown(ctx)
            return None
        return results

    def _manage_mentions(self, ctx, username, usernames):
        if not usernames:
            ping_user = self.db_actions.fetch_discord_id(username) if username else None
            return ctx.message.guild.get_member(ping_user).mention if ping_user else None
        else:
            mention_string = []
            for user in usernames:
                ping_user = self.db_actions.fetch_discord_id(user)
                discord_user = ctx.message.guild.get_member(ping_user)
                if discord_user is not None:
                    mention_string.append(discord_user.mention if ping_user else user)
                else:
                    mention_string.append(user)
            mention_list = list(filter(lambda mention: mention is not None, mention_string))
            return ", ".join(mention_list) if len(mention_list) > 0 else None

    async def _send_art_results(self, ctx, channel, in_results, message, username=None, usernames=None, display_num=None):
        display_count = self._check_your_privilege(ctx)
        display = display_count if (not display_num or display_num >= display_count) else display_num

        results = await self._filter_results(ctx, in_results, channel, "src_image", username) if not usernames \
            else in_results
        if not results:
            return

        mention_string = self._manage_mentions(ctx, username, usernames)
        final_message = message.format(mention_string) if mention_string and username else message

        embeds = []
        titles = []
        for result in results[:display]:
            embeds.append(BytesIO(requests.get(result['src_image']).content) if not usernames else
                          BytesIO(requests.get(result['media_content'][-1]['url']).content))
            titles.append(result['title'])
        amaztemp = Template(titles, embeds)
        thumbs = amaztemp.draw()
        with BytesIO() as image_binary:
            thumbs.save(image_binary, 'PNG')
            image_binary.seek(0)
            await channel.send(final_message, file=discord.File(image_binary, filename='thumbs.png'))
        # await channel.send(mention_string, embeds=embed) if mention_string else await channel.send(embeds=embed)
        self.db_actions.add_coins(ctx.message.author.id, username)

    async def _send_lit_results(self, ctx, channel, results, username=None, usernames=None, display_num=None):
        display_count = int(self._check_your_privilege(ctx))
        display = display_count if (not display_num or display_num >= display_count) else display_num

        results = await self._filter_results(ctx, results, channel, "src_snippet", username) if not usernames \
            else results
        if not results:
            return

        mention_string = self._manage_mentions(ctx, username, [])

        embed = discord.Embed()
        nl = '\n'
        for result in results[:display]:
            embed.add_field(
                name=f"{result['title']}: ({result['url']})",
                value=f"'{result['src_snippet'].replace('<br />', nl)}'",
                inline=False)
        await channel.send(mention_string, embed=embed) if mention_string else await channel.send(embed=embed)
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

    @commands.command(name='random')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def random(self, ctx):
        channel = self._set_channel(ctx, [THUMBHUB_CHANNEL, NSFW_CHANNEL])
        try:
            display_count = self._check_your_privilege(ctx)
            results, links = self.da_rss.get_random_images(display_count)
            message = f"{links}"
            usernames = [each[3:] for each in links.split(", ")]

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
            arg_dict['gallery'] = args[args.index("gallery") + 1]
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

    def _fetch_based_on_args(self, username, version, arg):
        offset = arg['offset'] if arg and 'offset' in arg.keys() else 0
        display_num = arg['show_only'] if arg and 'show_only' in arg.keys() else 24
        if arg:
            wants_random = 'random' in arg.keys()
            if 'pop' in arg.keys():
                pop = self.da_rest.fetch_user_popular(username, version, offset, display_num)
                if not wants_random:
                    return pop, offset, display_num
                random.shuffle(pop)
                return pop, offset, display_num
            elif 'old' in arg.keys():
                old = self.da_rest.fetch_user_old(username, version, offset, display_num)
                if not wants_random:
                    return old, offset, display_num
                random.shuffle(old)
                return old, offset, display_num
            elif 'gallery' in arg.keys():
                gallery = self.da_rest.get_user_gallery(username, version, arg['gallery'])
                if not wants_random:
                    return gallery, offset, display_num
                random.shuffle(gallery)
                return gallery, offset, display_num
            elif 'tags' in arg.keys():
                with_tags = self.da_rest.get_user_devs_by_tag(username, version, arg['tags'], offset, display_num)
                if not wants_random:
                    return with_tags, offset, display_num
                random.shuffle(with_tags)
                return with_tags, offset, display_num
            elif wants_random:
                results = self.da_rest.fetch_entire_user_gallery(username, version)
                random.shuffle(results)
                return results, offset, display_num

        return self.da_rest.fetch_user_gallery(username, version, offset, display_num), offset, display_num

    @commands.command(name='art')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def art(self, ctx, username, *args, channel=None):
        try:
            arg = self._parse_args(*args)
            if not channel:
                channel = self._set_channel(ctx, [THUMBHUB_CHANNEL, NSFW_CHANNEL])

            results, offset, display_num = self._fetch_based_on_args(username, "src_image", arg)

            if not results and username and arg and ('pop' in arg.keys() or 'old' in arg.keys()):
                await channel.send(f"{username} must be in store to use 'pop' and 'old'")
                ctx.command.reset_cooldown(ctx)
                return
            filtered_results = await self._filter_results(ctx, results, channel, "src_image", username)
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
        await self.favs(ctx, username, channel, *args)

    @commands.command(name='favs')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def favs(self, ctx, username, channel=None, *args):
        if not channel:
            channel = self._set_channel(ctx, [THUMBHUB_CHANNEL])

        num = self._check_your_privilege(ctx)
        arg = self._parse_args(*args)
        try:
            if arg and 'collection' in arg.keys():
                results, links = self.da_rest.get_user_favs_by_collection(username, "src_image", arg['collection'])
            else:
                results, links = self.da_rss.get_user_favs(username, num)

            if len(results) == 0 and username:
                await channel.send(f"Couldn't find any faves for {username}! Do they have any favorites?")
                ctx.command.reset_cooldown(ctx)
                return
            message = f"{links}"
            usernames = [each[3:] for each in links.split(", ")]
            await self._send_art_results(ctx, channel, results, message, usernames=usernames if not arg else None)
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

            results, offset, display_num = self._fetch_based_on_args(username, "src_snippet", arg)
            if not results and username and arg and ('pop' in arg.keys() or 'old' in arg.keys()):
                await channel.send(f"{username} must be in store to use 'pop' and 'old'")
                ctx.command.reset_cooldown(ctx)
                return
            await self._send_lit_results(ctx, channel, results, username=username, display_num=display_num)
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
            art = random.randint(0, 10) % 2 == 0
            results = await self._filter_results(ctx, results, channel, "src_image" if art else
                                                 "src_snippet")
            if not results and not art:
                art = True
                results = await self._filter_results(ctx, self.da_rest.fetch_daily_deviations(), channel, "src_image")
            if not results:
                await channel.send(f"Couldn't fetch dailies, try again.")
                return
            random.shuffle(results)
            result_string = [f"[[{index + 1}]({image['url']})] {image['author']}" for index, image in
                             enumerate(results[:self._check_your_privilege(ctx)])]
            message = f'''From today's [Daily Deviations](https://www.deviantart.com/daily-deviations): 
{", ".join(result_string)}'''
            await self._send_art_results(ctx, channel, results, message, username=ctx.message.author.display_name) if \
                art else await self._send_lit_results(ctx, channel, results)
        except Exception as ex:
            print(ex, flush=True)
            await channel.send(f"Something went wrong! {ex}")

            if channel.name == "bot-testing":
                raise Exception(ex)


async def setup(bot):
    await bot.add_cog(CreationCommands(bot))
