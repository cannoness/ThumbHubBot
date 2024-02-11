import math

from Utilities.DatabaseActions import DatabaseActions
from discord.ext import commands, tasks
from Cogs.CreationCommands import Private
import discord
import os
import random

from dotenv import load_dotenv
import datetime


load_dotenv()
GUILD_ID = int(os.getenv("GUILD_ID"))
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
        self.bot = bot
        self.guild = None
        self.db_actions = DatabaseActions()

        self.daily_reset.start()

    def cog_unload(self):
        self.daily_reset.cancel()

    @tasks.loop(hours=24)
    async def daily_reset(self):
        expiring_roles = self.db_actions.get_all_expiring_roles()
        if len(expiring_roles) > 0:
            for ids, colors in expiring_roles:
                discord_id = self.guild.get_member(ids)
                role = discord.utils.get(self.guild.roles, name=colors)
                await discord_id.remove_roles(role)
            self.db_actions.delete_role([ids[0] for ids in expiring_roles])
        self.db_actions.refresh_message_counts()
        bot_channel = self.bot.get_channel(int(BOT_TESTING_CHANNEL))
        if len(expiring_roles) > 0:
            await bot_channel.send(f"Resetting roles: {expiring_roles}")

    @daily_reset.before_loop
    async def before_daily_reset(self):
        print('waiting...')
        await self.bot.wait_until_ready()
        self.guild = self.bot.get_guild(GUILD_ID)

    @commands.command(name='store-da-name')
    async def store_name(self, ctx, username, discord_id: discord.Member = None):
        if not discord_id:
            discord_id = ctx.author
        self.db_actions.store_da_name(discord_id.id, username)
        await ctx.send(f"Storing or updating DA username {username} for user {discord_id.display_name}")

    @commands.command(name='store-random-da-name')
    async def store_random_name(self, ctx, username):
        self.db_actions.store_random_da_name(username)
        await ctx.send(f"Storing DA username {username} without private.custom_cooldown.")

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
        await ctx.channel.send(f"You currently have {math.floor(coins)} hubcoins.") if user is None else \
            await ctx.channel.send(f"{user.display_name} currently has {math.floor(coins)} hubcoins.")

    @commands.command(name='spend-hubcoins')
    async def spend_hubcoins(self, ctx, *message):
        current_coins = self.db_actions.get_hubcoins(ctx.message.author.id, "hubcoins")
        reason = message[0]
        amount = int(message[-1]) if message[-1].isdigit() else None
        reason_cost = 1 if 'xp' in reason else 100 if ("feature" in reason or "color" in reason) else 500 \
            if "vip" in reason else 1000 if "spotlight" in reason else 1 if "donate" in reason else None
        if not reason_cost or current_coins < reason_cost:
            await ctx.channel.send(f"Sorry, you need {int(reason_cost)-int(current_coins)} more hubcoins to perform "
                                   f"this action.") if \
                reason_cost else await ctx.channel.send(f"Invalid spend reason supplied! You may spend on 'xp', "
                                                        f"'feature', 'vip', 'color', 'spotlight' or 'donate'."
                                                        f" Please try again.")
            return
        if not amount:
            amount = reason_cost
        self.db_actions.spend_coins(ctx.message.author.id, amount)
        mod_channel = self.bot.get_channel(int(MOD_CHANNEL))
        # refactor this
        if "color" in reason:
            author = ctx.message.author
            current_roles = [role.name for role in ctx.message.author.roles]
            color = message[-1].title() if not message[-1].isdigit() else " ".join(message[1:len(message)-1]).title()
            role = "mod" if "Moderators" in current_roles else "FT" if "Frequent Thumbers" in current_roles else "Dev"
            desired_color = f'{color} ({role})'
            role = discord.utils.get(author.guild.roles, name=desired_color)

            if not role:
                await ctx.channel.send(f"No role color found, a mod will DM you soon or correct manually.")
                await mod_channel.send(f"Unable to assign '{desired_color}' role to "
                                       f"{ctx.message.author.display_name}")
            await author.add_roles(role)
            self.db_actions.add_role_timer(ctx.message.author.id, desired_color)
            await ctx.channel.send(f"Congratulations on your new role color! Color will expire in 1 week")
            return
        else:
            await ctx.channel.send(f"You have spent {amount} hubcoins on {reason}. A mod will contact you soon.")
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

    @commands.hybrid_command(name="help", with_app_command=True)
    async def help(self, interaction, command: str = None, list_commands: bool = False, anon: bool = True) -> None:
        admin = ['cpr', 'dm-server', 'fund-hubcoins', 'sync', 'rank', 'levels', 'help', 'spent-hubcoins']

        embed = discord.Embed(
            title='ThumbHubBot Help Menu',
            description='',
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)

        if list_commands:
            all_commands = [command.name for command in self.bot.walk_commands() if command.name not in admin]
            command_list = ", ".join(sorted(all_commands))

            embed.add_field(name='The following server commands are available',
                            value=f"{command_list}",
                            inline=False)
            embed.add_field(name='\u200b',
                            value=f"For usage options of a specific command, call /help again with that command name.",
                            inline=False)
        elif command == 'art':
            embed.description = f"""Documentation for command '!art'
`!art deviantart-username`
Pulls the first n number of deviations from the 'All' gallery of the provided deviantart account username.

`!art deviantart-username rnd`
Pulls n random deviations for the given deviantart user.

`!art deviantart-username +offset`
Pulls n deviations, starting with the offset number given. E.g. +1 would skip the first deviation in the gallery.

`!art deviant-username 1`
Shows the first deviation in the user's gallery.

`!art deviant-username pop`
Shows popular deviations of the deviant.*

`!art deviant-username old`
Shows old deviations of the deviant.*"""

            embed.set_footer(text="*Only works if the user is saved the ThumbHub store (see command "
                                  f"store-random-da-name)")

        elif command == 'hubcoins':
            embed.description('Documentation for command "!hubcoins"')
            embed.add_field(name='!hubcoins',
                            value=f"See how many hubcoins you currently have."
                                  f"<b>!hubcoins @user</b><br>"
                                  f"See how many hubcoins another user currently has.",
                            inline=False)

        await interaction.interaction.response.send_message(embed=embed, ephemeral=anon)
        # await interaction.interaction.followup.send(f'testing help command', ephemeral=anon)

    @commands.hybrid_command(name="whois", with_app_command=True)
    async def whois(self, interaction, user: discord.User, anon: bool) -> None:
        await interaction.interaction.response.send_message(f'testing whois command',
                                                            ephemeral=anon)

    @commands.hybrid_command(name="stats", with_app_command=True)
    async def stats(self, interaction, user: discord.User, anon: bool) -> None:
        await interaction.interaction.response.send_message(f'testing stats command',
                                                            ephemeral=anon)


async def setup(bot):
    await bot.add_cog(SpecialCommands(bot))
