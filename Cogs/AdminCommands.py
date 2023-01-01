from discord.ext import commands
import discord


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
