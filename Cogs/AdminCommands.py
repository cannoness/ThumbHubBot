from discord.ext import commands
from Utilities.DA_rest import DARest
import discord


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.da_rest = DARest()

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
    async def refund_hubcoins(self, ctx, discord_id, amount):
        user_roles = set([role.name for role in ctx.message.author.roles])
        if {"The Hub", "Moderators"}.isdisjoint(user_roles):
            return
        else:
            self.da_rest.add_coins(discord_id.id, amount)
            await ctx.message.channel.send(f"Refunded {amount} hubcoins to {discord_id.nickname}")


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
