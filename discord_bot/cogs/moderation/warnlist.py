import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.database import execute, fetchall
from core.dbconstants import WarnTable
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class WarnList(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Moderation,
        is_dm_only=False,
        is_server_only=True,
        subcommands=None,
        permissions=["`Kick, Approve and Reject Members`"],
        help_=None,
        brief="Shows warnings of a member from the server.",
        usage='<target (mention *or* ID *or* "all")[*optional*]>',
        aliases=["wl", "warns"],
    )

    @commands.command(name="warnlist", **Help.to_kwargs)
    async def warnlist(
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.User | int | str | None = None,
    ):
        # if user runs the command in dm
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return await ctx.reply("You can only run moderation commands in a server.")

        # if the user has no permission to to see the warns
        if not ctx.author.guild_permissions.kick_members:
            return await ctx.reply(
                "You have no permission to *see the warnings* of Members."
            )

        # if the bot has no permission to see the warns
        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.reply(
                "I have no permission to *see the warnings* of Members."
            )

        # if user mentions an invalid user
        if isinstance(user, str) and user.lower() != "all":
            raise commands.BadArgument

        # shows warns of the target user
        if user and not isinstance(user, str):
            try:
                target = (
                    (self.bot.get_user(user) or await self.bot.fetch_user(user))
                    if isinstance(user, int)
                    else user
                )  # trys to fetch the target if id is given
            except discord.NotFound:
                return await ctx.reply(f"User with this ID doesn't exist.")

            # if user trys to see the server owner warns
            if target.id == ctx.guild.owner_id:
                return await ctx.reply("Server *Owner* has no warning i guess?")

            # if user wants to run moderation command on the bot
            if target.id == ctx.me.id:
                return await ctx.reply("I have no warnings for you to see. agh.")

            # if user wants to see bots warnings
            if target.bot:
                return await ctx.reply("Bots have no warning for you to see.")

            # searchs database with given arguments
            row = await fetchall(
                f"""
                SELECT * FROM {WarnTable.TABLE_NAME}
                WHERE {WarnTable.COL_SERVER_ID} = ? AND {WarnTable.COL_USER_ID} = ?
                ORDER BY {WarnTable.COL_TIMESTAMP};
                """,
                (ctx.guild.id, target.id),
            )

            warns: list[str] = []  # a list to store warnings
            if row:
                for number, warn in enumerate(row, start=1):
                    # trys to find moderator name
                    try:
                        moderatorUser = (
                            (
                                self.bot.get_user(warn["mod_id"])
                                or await self.bot.fetch_user(warn["mod_id"])
                            )
                            if warn["mod_id"]
                            else None
                        )
                    except Exception:
                        moderatorUser = None
                    moderatorName = (
                        moderatorUser.mention if moderatorUser else "*unknown*"
                    )
                    desc = f"{number}. Warn ID: {warn['user_warn_id']} | Reason: {warn['reason'] if warn['reason'] else '*no reason provided*'} | Moderator: {moderatorName} | Date: {warn['timestamp']}"
                    warns.append(desc)

            resultEmbed = discord.Embed(
                title=f"{target.display_name}'s warnings",
                description=(
                    "\n".join(warns) if warns else f"{target.mention} has no warnings."
                ),
                color=discord.Color.dark_blue(),
            )
            await ctx.reply(embed=resultEmbed)

        # shows all warn list
        else:
            # searchs database with given arguments
            row = await fetchall(
                f"""
                SELECT * FROM {WarnTable.TABLE_NAME}
                WHERE {WarnTable.COL_SERVER_ID} = ?
                ORDER BY {WarnTable.COL_TIMESTAMP};
                """,
                (ctx.guild.id,),
            )

            warns: list[str] = []  # a list to store all server warns
            if row:
                for number, warn in enumerate(row, start=1):
                    # trys to find the target
                    try:
                        target = self.bot.get_user(
                            warn["user_id"]
                        ) or await self.bot.fetch_user(warn["user_id"])
                    except discord.NotFound:
                        # if fetched target user doesn't exist, deletes the warning
                        await execute(
                            f"""
                            DELETE FROM {WarnTable.TABLE_NAME}
                            WHERE {WarnTable.COL_ID} = ?;
                            """,
                            (warn["warn_id"],),
                        )
                        continue

                    # trys to find moderators name
                    try:
                        moderatorUser = (
                            (
                                self.bot.get_user(warn["mod_id"])
                                or await self.bot.fetch_user(warn["mod_id"])
                            )
                            if warn["mod_id"]
                            else None
                        )
                    except Exception:
                        moderatorUser = None
                    moderatorName = (
                        moderatorUser.mention if moderatorUser else "*unknown*"
                    )
                    desc = f"{number}. Warn ID: {warn['user_warn_id']} | User: {target.display_name} | Reason: {warn['reason'] if warn['reason'] else '*no reason provided*'} | Moderator: {moderatorName} | Date: {warn['timestamp']}"
                    warns.append(desc)

            resultEmbed = discord.Embed(
                title=f"{ctx.guild.name}'s warning list",
                description=(
                    "\n".join(warns)
                    if warns
                    else f"There is no warning commited yet in this server."
                ),
                color=discord.Color.dark_blue(),
            )
            await ctx.reply(embed=resultEmbed)

    @warnlist.error
    async def warnlist_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ):
        # if user entered an invalid user
        if isinstance(error, commands.BadArgument):
            await ctx.reply("User not found. Please mention a valid user.")
        else:
            logger.exception(f"❌ something went wrong with warnlist command:")
            await ctx.reply("something went wrong with **warnlist**.")

    # warnlist slash command
    @app_commands.command(name="warnlist", description=Help.brief, extras=Help.extras)
    @app_commands.guild_only()
    @app_commands.describe(user="The target user to get warning list for.")
    async def slashWarnlist(
        self, interaction: discord.Interaction, user: discord.User | None = None
    ):
        # if user runs the command in dm
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You can only run moderation commands in a server.", ephemeral=True
            )

        # if the user has no permission to to see the warns
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message(
                "You have no permission to *see the warnings* of Members.",
                ephemeral=True,
            )

        # if the bot has no permission to see the warns
        if not interaction.guild.me.guild_permissions.kick_members:
            return await interaction.response.send_message(
                "I have no permission to *see the warnings* of Members.", ephemeral=True
            )

        # shows warns of the target user
        if user:
            # if user trys to see the server owner warns
            if user.id == interaction.guild.owner_id:
                return await interaction.response.send_message(
                    "Server *Owner* has no warning i guess?", ephemeral=True
                )

            # if user wants to run moderation command on the bot
            if user.id == interaction.client.application_id:
                return await interaction.response.send_message(
                    "I have no warnings for you to see. agh.", ephemeral=True
                )

            # if user wants to see bots warnings
            if user.bot:
                return await interaction.response.send_message(
                    "Bots have no warning for you to see.", ephemeral=True
                )

            # searchs database with given arguments
            row = await fetchall(
                f"""
                SELECT * FROM {WarnTable.TABLE_NAME}
                WHERE {WarnTable.COL_SERVER_ID} = ? AND {WarnTable.COL_USER_ID} = ?
                ORDER BY {WarnTable.COL_TIMESTAMP};
                """,
                (interaction.guild.id, user.id),
            )

            warns: list[str] = []  # a list to store warnings
            if row:
                for number, warn in enumerate(row, start=1):
                    # trys to find moderator name
                    try:
                        moderatorUser = (
                            (
                                self.bot.get_user(warn["mod_id"])
                                or await self.bot.fetch_user(warn["mod_id"])
                            )
                            if warn["mod_id"]
                            else None
                        )
                    except Exception:
                        moderatorUser = None
                    moderatorName = (
                        moderatorUser.mention if moderatorUser else "*unknown*"
                    )
                    desc = f"{number}. Warn ID: {warn['user_warn_id']} | Reason: {warn['reason'] if warn['reason'] else '*no reason provided*'} | Moderator: {moderatorName} | Date: {warn['timestamp']}"
                    warns.append(desc)

            resultEmbed = discord.Embed(
                title=f"{user.display_name}'s warnings",
                description=(
                    "\n".join(warns) if warns else f"{user.mention} has no warnings."
                ),
                color=discord.Color.dark_blue(),
            )
            await interaction.response.send_message(embed=resultEmbed)

        # shows all warn list
        else:
            # searchs database with given arguments
            row = await fetchall(
                f"""
                SELECT * FROM {WarnTable.TABLE_NAME}
                WHERE {WarnTable.COL_SERVER_ID} = ?
                ORDER BY {WarnTable.COL_TIMESTAMP};
                """,
                (interaction.guild.id,),
            )

            warns: list[str] = []  # a list to store all server warns
            if row:
                for number, warn in enumerate(row, start=1):
                    # trys to find the target
                    try:
                        target = self.bot.get_user(
                            warn["user_id"]
                        ) or await self.bot.fetch_user(warn["user_id"])
                    except discord.NotFound:
                        # if fetched target user doesn't exist, deletes the warning
                        await execute(
                            f"""
                            DELETE FROM {WarnTable.TABLE_NAME}
                            WHERE {WarnTable.COL_ID} = ?;
                            """,
                            (warn["warn_id"],),
                        )
                        continue

                    # trys to find moderators name
                    try:
                        moderatorUser = (
                            (
                                self.bot.get_user(warn["mod_id"])
                                or await self.bot.fetch_user(warn["mod_id"])
                            )
                            if warn["mod_id"]
                            else None
                        )
                    except Exception:
                        moderatorUser = None
                    moderatorName = (
                        moderatorUser.mention if moderatorUser else "*unknown*"
                    )
                    desc = f"{number}. Warn ID: {warn['user_warn_id']} | User: {target.display_name} | Reason: {warn['reason'] if warn['reason'] else '*no reason provided*'} | Moderator: {moderatorName} | Date: {warn['timestamp']}"
                    warns.append(desc)

            resultEmbed = discord.Embed(
                title=f"{interaction.guild.name}'s warning list",
                description=(
                    "\n".join(warns)
                    if warns
                    else f"There is no warning commited yet in this server."
                ),
                color=discord.Color.dark_blue(),
            )
            await interaction.response.send_message(embed=resultEmbed)

    @slashWarnlist.error
    async def slashWarnlist_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        logger.exception(f"❌ something went wrong with /warnlist command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **warnlist**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **warnlist**.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(WarnList(bot))
