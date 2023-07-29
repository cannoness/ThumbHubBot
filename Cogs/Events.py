import os
from dotenv import load_dotenv
from discord.ext import commands

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

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:  # skip bot messages
            return
        if message.channel.id == int(BOT_TESTING_CHANNEL):
            # await message.channel.send(f'counting {message.author.name}')  # placeholder for auto-coin
            pass


async def setup(bot):
    await bot.add_cog(Events(bot))
