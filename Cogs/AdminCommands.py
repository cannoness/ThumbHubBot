import discord

from json import loads
from typing import Optional, Literal
from discord.ext import commands
from discord.ext.commands import Context, Greedy

from Utilities.DARest import DARest
from Utilities.DatabaseActions import DatabaseActions
from thumbhubbot import CONFIG, ROLESET, ROLE, LOGGER


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.da_rest = DARest()
        self.db_actions = DatabaseActions()

    # ADMIN ONLY, USE SPARINGLY
    @commands.command(name='dm-server')
    async def dm_server(self, ctx, message):
        user_roles = [role.name for role in ctx.message.author.roles]
        if ROLE.the_hub not in user_roles:
            return
        else:
            embed = discord.Embed(description=message)
            for user in ctx.guild.members:
                try:
                    await user.send(embed=embed)
                except Exception as ex:
                    LOGGER.error(ex, stack_info=True)
                    continue

    @commands.command(name='send-announcement-embed')
    async def create_embed(self, ctx):
        user_roles = [role.name for role in ctx.message.author.roles]
        if ROLESET.admins.isdisjoint(user_roles):
            return
        else:
            channel = self.bot.get_channel(CONFIG.tannouncements_channel)
            try:
                with open(CONFIG.json_file, "r") as file:
                    embed = discord.Embed().from_dict(loads(file.read()))
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
                file = discord.File("dummy_img.jpg", filename="dummy_img.jpg")
                embed.set_thumbnail(url="attachment://dummy_img.jpg")
                allowed_mentions = discord.AllowedMentions(everyone=True)
                await channel.send(allowed_mentions=allowed_mentions, file=file, embed=embed)
            except Exception as ex:
                raise Exception(ex)

    @commands.command(name='cpr')
    async def health_check(self, ctx):
        user_roles = set([role.name for role in ctx.message.author.roles])
        if ROLESET.admins.isdisjoint(user_roles):
            return
        else:
            await ctx.message.channel.send("I AM STILL ALIVE (and doing science)")

    @commands.command(name='fund-hubcoins')
    async def fund_hubcoins(self, ctx, discord_id: discord.Member, amount):
        user_roles = set([role.name for role in ctx.message.author.roles])
        if ROLESET.admins.isdisjoint(user_roles):
            return
        else:
            self.db_actions.update_coins(discord_id.id, int(amount))
            await ctx.message.channel.send(f"Funded {amount} hubcoins to {discord_id.display_name}")

    @commands.command(name='spent-hubcoins')
    async def spent_hubcoins(self, ctx, discord_id: discord.Member):
        user_roles = set([role.name for role in ctx.message.author.roles])
        if ROLESET.admins.isdisjoint(user_roles):
            return
        else:
            coins = self.db_actions.get_hubcoins(discord_id.id, "spent_coins")
            await ctx.message.channel.send(f"{discord_id.display_name} has spent {coins} hubcoins total")

    @commands.command(name="sync")
    async def sync(
            self, ctx: Context, guilds: Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None
    ) -> None:
        user_roles = set([role.name for role in ctx.message.author.roles])
        if ROLESET.admins.isdisjoint(user_roles):
            return
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                ctx.bot.tree.clear_commands(guild=None)
                [ctx.bot.tree.remove_command(c.name) for c in self.bot.tree.get_commands()]
                synced = [c.name for c in self.bot.tree.get_commands()]
            else:
                synced = await ctx.bot.tree.sync(guild=ctx.guild)

            bcommands = [c.name for c in self.bot.tree.get_commands()]
            LOGGER.debug(f"registered commands: {', '.join(bcommands)}")
            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0

        try:
            await ctx.bot.tree.sync()
        except discord.HTTPException as ex:
            LOGGER.error(ex, stack_info=True)
            await ctx.send(f"Encountered exception {ex}. This has been recorded.")
            raise Exception(ex)
        else:
            ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
