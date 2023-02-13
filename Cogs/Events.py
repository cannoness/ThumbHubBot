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
            await ctx.send(f"{error}")
            print("command didn't work.")
        if isinstance(error, commands.errors.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            await ctx.send(f"This command is on cooldown for user {ctx.message.author.display_name}, try again after "
                           f"{int(minutes)}m {int(seconds)}s.", ephemeral=True)
            print("command didn't work.")


async def setup(bot):
    await bot.add_cog(Events(bot))
