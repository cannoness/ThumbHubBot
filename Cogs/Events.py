import os
import traceback
from types import TracebackType

from dotenv import load_dotenv
from discord.ext import commands
from Utilities.DatabaseActions import DatabaseActions

load_dotenv()
THUMBHUB_CHANNEL = os.getenv("THUMBHUB_CHANNEL")
THE_PEEPS = os.getenv("STREAMS_N_THINGS")
MOD_CHANNEL = os.getenv("MOD_CHANNEL")
NSFW_CHANNEL = os.getenv("NSFW_CHANNEL")
BOT_TESTING_CHANNEL = os.getenv("BOT_TESTING_CHANNEL")
PRIVILEGED_ROLES = {'Frequent Thumbers', "Veteran Thumbers", "the peeps"}


class Events(commands.Cog):
    def __init__(self, bot_):
        self.bot = bot_
        self.db_actions = DatabaseActions()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.bot.user} has connected to Discord!')

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

        bot_channel = self.bot.get_channel(int(BOT_TESTING_CHANNEL))
        await bot_channel.send(f"Error encountered: {error}.")
        return await ctx.send(f"Error was encountered! Logged to admins.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:  # skip bot messages
            return
        if message.channel.id in [int(THUMBHUB_CHANNEL), int(THE_PEEPS), int(NSFW_CHANNEL)]:
            diminish_by = self.db_actions.diminish_coins_added(message.author.id)
            coins_to_add = 1 - 1*diminish_by
            self.db_actions.update_coins(message.author.id, coins_to_add)


async def setup(bot):
    await bot.add_cog(Events(bot))
