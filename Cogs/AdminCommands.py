from discord.ext import commands
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


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
