from types import TracebackType
from discord.ext import commands

from thumbhubbot import CONFIG, LOGGER
from Utilities.DatabaseActions import DatabaseActions


class Events(commands.Cog):
    def __init__(self, bot_):
        self.bot = bot_
        self.db_actions = DatabaseActions()

    @commands.Cog.listener()
    async def on_ready(self):
        LOGGER.info(f'{self.bot.user} has connected to Discord!')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            ctx.command.reset_cooldown(ctx)
            tb = TracebackType.tb_next
            return await ctx.send(f"{error.with_traceback(tb)}")
        if isinstance(error, commands.errors.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            return await ctx.send(f"This command is on cooldown for user {ctx.message.author.display_name}, "
                                  f"try again after {int(minutes)}m {int(seconds)}s.", ephemeral=True)
        if isinstance(error, commands.errors.CommandNotFound):
            return await ctx.send(f"This command does not exist.", ephemeral=True)

        bot_channel = self.bot.get_channel(CONFIG.bot_channel)
        await bot_channel.send(f"Error encountered: {error}.")
        return await ctx.send(f"Error was encountered! Logged to admins.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:  # skip bot messages
            return
        if message.channel.id in [CONFIG.thumbhub_channel, CONFIG.the_peeps, int(CONFIG.nsfw_channel)]:
            diminish_by = self.db_actions.diminish_coins_added(message.author.id)
            coins_to_add = 1 - 1*diminish_by
            self.db_actions.update_coins(message.author.id, coins_to_add)


async def setup(bot):
    await bot.add_cog(Events(bot))
