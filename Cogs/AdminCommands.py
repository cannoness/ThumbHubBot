from typing import Optional, Literal

from discord.ext import commands
from discord.ext.commands import Context, Greedy

from Utilities.DARest import DARest
from Utilities.DatabaseActions import DatabaseActions
import discord


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.da_rest = DARest()
        self.db_actions = DatabaseActions()

    # ADMIN ONLY, USE SPARINGLY
    @commands.command(name='dm-server')
    async def dm_server(self, ctx, message):
        user_roles = [role.name for role in ctx.message.author.roles]
        if "The Hub" not in user_roles:
            return
        else:
            embed = discord.Embed(description=message)
            for user in ctx.guild.members:
                try:
                    await user.send(embed=embed)
                except Exception as ex:
                    print(ex)
                    continue

    @commands.command(name='cpr')
    async def health_check(self, ctx):
        user_roles = set([role.name for role in ctx.message.author.roles])
        if {"The Hub", "Moderators"}.isdisjoint(user_roles):
            return
        else:
            await ctx.message.channel.send("I AM STILL ALIVE (and doing science)")

    @commands.command(name='refund-hubcoins')
    async def refund_hubcoins(self, ctx, discord_id: discord.Member, amount):
        user_roles = set([role.name for role in ctx.message.author.roles])
        if {"The Hub", "Moderators"}.isdisjoint(user_roles):
            return
        else:
            self.db_actions.update_coins(discord_id.id, int(amount))
            await ctx.message.channel.send(f"Refunded {amount} hubcoins to {discord_id.display_name}")

    @commands.command(name='spent-hubcoins')
    async def spent_hubcoins(self, ctx, discord_id: discord.Member):
        user_roles = set([role.name for role in ctx.message.author.roles])
        if {"The Hub", "Moderators"}.isdisjoint(user_roles):
            return
        else:
            coins = self.db_actions.get_hubcoins(discord_id.id, "spent_coins")
            await ctx.message.channel.send(f"{discord_id.display_name} has spent {coins} hubcoins total")

    @commands.command(name="sync")
    async def sync(self, ctx: Context, guilds: Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) \
            -> None:
        user_roles = set([role.name for role in ctx.message.author.roles])
        if {"The Hub", "Moderators"}.isdisjoint(user_roles):
            return
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            bcommands = [c.name for c in self.bot.tree.get_commands()]
            print(f"registered commands: {', '.join(bcommands)}")
            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0

        try:
            await ctx.bot.tree.sync()
        except discord.HTTPException as ex:
            print(ex)
        else:
            ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
