from discord import app_commands
from discord.app_commands import command

from Utilities.DatabaseActions import DatabaseActions
from discord.ext import commands
from Cogs.CreationCommands import Private
import discord
import os
import random

from dotenv import load_dotenv
import datetime


load_dotenv()
ART_LIT_CHANNEL = os.getenv("ART_LIT_CHANNEL")
BOT_TESTING_CHANNEL = os.getenv("BOT_TESTING_CHANNEL")
MOD_CHANNEL = os.getenv("MOD_CHANNEL")
PRIVILEGED_ROLES = {'Frequent Thumbers', 'Moderators', 'The Hub'}
VIP_ROLE = "THE HUB VIP"
COOLDOWN_WHITELIST = {"Moderators", "The Hub", "Bot Sleuth"}
PRIV_COUNT = 4
DEV_COUNT = 2
DEFAULT_COOLDOWN = 300
VIP_COOLDOWN = 180
POST_RATE = 1


class SpecialCommands(commands.Cog):
    def __init__(self, bot):
        seed = os.getpid()+int(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        random.seed(seed)

        self.bot = bot
        self.db_actions = DatabaseActions()

    @commands.command(name='store-da-name')
    async def store_name(self, ctx, username, discord_id: discord.Member = None):
        if not discord_id:
            discord_id = ctx.author
        print(discord_id)
        self.db_actions.store_da_name(discord_id.id, username)
        await ctx.send(f"Storing or updating DA username {username} for user {discord_id.display_name}")

    @commands.command(name='store-random-da-name')
    async def store_random_name(self, ctx, username):
        self.db_actions.store_random_da_name(username)
        await ctx.send(f"Storing DA username {username} without mention.")

    @commands.cooldown(POST_RATE, DEFAULT_COOLDOWN, commands.BucketType.user)
    @commands.command(name='roll')
    async def roll_dice(self, ctx):
        await ctx.send(f"{ctx.message.author.display_name} Rolling 1d20: {random.randint(1, 20)}")

    @commands.command(name='nomention')
    async def do_not_mention(self, ctx, user: discord.Member):
        self.db_actions.do_not_ping_me(user.id)
        await ctx.channel.send(f"We will no longer mention you {user.display_name}")

    @commands.command(name='mention')
    async def mention(self, ctx, user: discord.Member):
        self.db_actions.ping_me(user.id)
        await ctx.channel.send(f"We will now mention you {user.display_name}")

    @commands.command(name='hubcoins')
    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    async def hubcoins(self, ctx, user: discord.Member = None):
        if user:
            coins = self.db_actions.get_hubcoins(user.id, "hubcoins")
        else:
            coins = self.db_actions.get_hubcoins(ctx.message.author.id, "hubcoins")
        await ctx.channel.send(f"You currently have {coins} hubcoins.") if user is None else \
            await ctx.channel.send(f"{user.display_name} currently has {coins} hubcoins.")

    @commands.command(name='spend-hubcoins')
    async def spend_hubcoins(self, ctx, reason, amount=None):
        current_coins = self.db_actions.get_hubcoins(ctx.message.author.id, "hubcoins")
        reason_cost = 1 if 'xp' in reason else 100 if "feature" in reason else 500 if "vip" in reason else 1000 if \
            "spotlight" in reason else 1 if "donate" in reason else None
        if not reason_cost or current_coins < reason_cost:
            await ctx.channel.send(f"Sorry, you need {int(reason_cost)-int(current_coins)} more hubcoins to perform "
                                   f"this action.") if \
                reason_cost else await ctx.channel.send(f"Invalid spend reason supplied! You may spend on 'xp', "
                                                        f"'feature', 'vip', 'spotlight' or 'donate'. Please try again.")
            return
        if not amount:
            amount = reason_cost
        self.db_actions.spend_coins(ctx.message.author.id, amount)
        await ctx.channel.send(f"You have spent {amount} hubcoins on {reason}. A mod will contact you soon.")
        mod_channel = self.bot.get_channel(int(MOD_CHANNEL))
        await mod_channel.send(f"{ctx.message.author.display_name} has spent {amount} hubcoins on {reason}")

    @commands.dynamic_cooldown(Private.custom_cooldown, type=commands.BucketType.user)
    @commands.hybrid_command(name="joycard", with_app_command=True)
    async def joycard(self, interaction, user: discord.User, message: str, anon: bool) -> None:
        try:
            coins = self.db_actions.get_hubcoins(interaction.author.id, "hubcoins")
            if int(coins) >= 1:
                embed = discord.Embed(title=":two_hearts: Someone has sent you a Joy Card! :two_hearts:" if anon else
                                      f":two_hearts: You have been sent a Joy Card from ThumbHub Member "
                                      f"{interaction.author} :two_hearts:",
                                      color=discord.Color.from_rgb(245, 130, 216), description=f"{message}"
                                                                                               f"\n\u200b\n\u200b")
                embed.add_field(value=f"If this message was inappropriate, please DM "
                                      f"{interaction.message.guild.get_member(162740078031011840)} "
                                      f"with what was sent to report it; we will take care of it.", name="",
                                inline=False)

                embed.add_field(name="", value="[From the ThumbHub Team](https://discord.gg/yJberKm)", inline=False)
                embed.set_thumbnail(url=interaction.author.avatar) if not anon else \
                    embed.set_thumbnail(url="https://img.freepik.com/free-icon/anonymous_318-504704.jpg")
                sent = await user.send(embed=embed)
                if sent:
                    await interaction.interaction.response.send_message(f'Sent {message} to {user.name} '
                                                                        f'{"anonymously" if anon else ""}',
                                                                        ephemeral=True)
                    self.db_actions.spend_coins(interaction.message.author.id, 1)
                    coins = self.db_actions.get_hubcoins(interaction.message.author.id, "hubcoins")
                    await interaction.interaction.followup.send(f"Grats! You have {coins} hubcoins remaining!",
                                                                ephemeral=True)
                    print(f"Sent by {interaction.author.display_name} to {user.display_name} "
                          f"{'anonymously' if anon else ''}")
            else:
                await interaction.interaction.response.send_message(f'You currently have {coins} hubcoins and need '
                                                                    f'{1-int(coins)} more to send a card',
                                                                    ephemeral=True)
        except Exception as ex:
            await interaction.interaction.response.send_message(f"We're sorry, this message could not be sent. "
                                                                f"This person may not be accepting messages from "
                                                                f"non-friends or have the bot blocked.",
                                                                ephemeral=True)
            print(ex)


async def setup(bot):
    await bot.add_cog(SpecialCommands(bot))
