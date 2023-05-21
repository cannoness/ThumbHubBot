from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.bot.user} has connected to Discord!')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f"{error}")
        if isinstance(error, commands.errors.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            return await ctx.send(f"This command is on cooldown for user {ctx.message.author.display_name}, "
                                  f"try again after {int(minutes)}m {int(seconds)}s.", ephemeral=True)
        return await ctx.send(f"{error}")


async def setup(bot):
    await bot.add_cog(Events(bot))
