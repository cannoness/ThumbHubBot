import os
from dotenv import load_dotenv
from discord.ext import commands
from Utilities.DatabaseActions import DatabaseActions

load_dotenv()
ART_LIT_CHANNEL = os.getenv("ART_LIT_CHANNEL")
MOD_CHANNEL = os.getenv("MOD_CHANNEL")
NSFW_CHANNEL = os.getenv("NSFW_CHANNEL")
BOT_TESTING_CHANNEL = os.getenv("BOT_TESTING_CHANNEL")
DISCOVERY_CHANNEL = os.getenv("DISCOVERY_CHANNEL")
PRIVILEGED_ROLES = {'Frequent Thumbers'}


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
            return await ctx.send(f"{error}")
        if isinstance(error, commands.errors.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            return await ctx.send(f"This command is on cooldown for user {ctx.message.author.display_name}, "
                                  f"try again after {int(minutes)}m {int(seconds)}s.", ephemeral=True)
        if isinstance(error, commands.errors.CommandOnCooldown):
            await ctx.send(f"This command does not exist", ephemeral=True)

        bot_channel = self.bot.get_channel(int(BOT_TESTING_CHANNEL))
        bot_channel.send(f"Error encountered: {error}.")
        return await ctx.send(f"Error was encountered! Logged to admins.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:  # skip bot messages
            return
        if message.channel.id in [int(ART_LIT_CHANNEL), int(DISCOVERY_CHANNEL), int(NSFW_CHANNEL)]:
            diminish_by = self.db_actions.diminish_coins_added(message.author.id)
            coins_to_add = 1 - 1*diminish_by
            self.db_actions.update_coins(message.author.id, coins_to_add)


async def setup(bot):
    await bot.add_cog(Events(bot))
