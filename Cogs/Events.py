from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.bot.user} has connected to Discord!')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        channel = await self.bot.fetch_channel(ctx.channel)
        if isinstance(error, commands.MissingRequiredArgument):
            ctx.command.reset_cooldown(ctx)
            await channel.send(f"{error}")
            print("command didn't work.")
        if isinstance(error, commands.errors.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            await channel.send(f"This command is on cooldown for user {ctx.message.author.display_name}, "
                               f"try again after {int(minutes)}m {int(seconds)}s.", ephemeral=True)
            print("command didn't work.")
        await channel.send(f"{error}")


async def setup(bot):
    await bot.add_cog(Events(bot))
