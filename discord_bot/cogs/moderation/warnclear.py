import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.database import execute, fetchall, fetchone
from core.dbconstants import WarnTable
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class WarnClear(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Moderation,
        is_dm_only=False,
        is_server_only=True,
        subcommands=None,
        permissions=["`Kick, Approve and Reject Members`"],
        help_=None,
        brief="Clears warnings of a member from the server.",
        usage='<target (mention *or* id)> <warn ID (*or* "all")[*optional*]> <reason[*optional*]>',
        aliases=["wc", "warnremove", "wr"],
    )

    @commands.command(name="warnclear", **Help.to_kwargs)
    async def warnclear(
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.User | int | str | None,
        warnId: int | str | None = None,
        *,
        reason: str | None = None,
    ):
        # if user runs the command in dm
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return await ctx.reply("You can only run moderation commands in a server.")

        # if the user has no permission to clear warns
        if not ctx.author.guild_permissions.kick_members:
            return await ctx.reply(
                "You have no permission to *clear* Members' warnings."
            )

        # if the bot has no permission to clear warns
        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.reply("I have no permisson to *clear* Members' warnings.")

        # if user didn't enter any target member
        if not user:
            return await ctx.reply("You must mention a target Member for this command.")

        # if user mentions an invalid user
        if not isinstance(user, (discord.abc.User, int)):
            raise commands.BadArgument

        try:
            user = (
                (self.bot.get_user(user) or await self.bot.fetch_user(user))
                if isinstance(user, int)
                else user
            )  # trys to fetch the target if id is given
        except discord.NotFound:
            return await ctx.reply(f"User with given ID doesn't exist.")

        target = ctx.guild.get_member(
            user.id
        )  # fetches the target user from the server, None if not found
        if not target:
            return await ctx.reply(
                f"{user.display_name} is not a Member of this server."
            )

        # if user wants to clear its own warns
        if target.id == ctx.author.id:
            return await ctx.reply("You can't clear your own warnings.")

        # if user wants to clear warns of the server owner
        if target.id == ctx.guild.owner_id:
            return await ctx.reply(
                "Server *Owner* has no warning for you to remove it now."
            )

        # if user wants to run moderation command on the bot
        if target.id == ctx.me.id:
            return await ctx.reply("I have no warning for you to remove it now??.")

        # if user wants to clear warns of bots
        if target.bot:
            return await ctx.reply("Bots have no warning for you to remove it now.")

        # if user has lower or equal role position than target
        if (
            target.top_role >= ctx.author.top_role
            and ctx.author.id != ctx.guild.owner_id
        ):
            return await ctx.reply(
                "You can't clear warn of a Member with *higher or equal* role position as you."
            )

        # if the bot has lower or equal role position than target
        if target.top_role >= ctx.guild.me.top_role:
            return await ctx.reply(
                "I can't clear warn of a Member with *higher or equal* role position as me."
            )

        # if user doesn't enter a valid warn id
        if isinstance(warnId, str) and warnId.lower() != "all":
            return await ctx.reply(
                'You must enter a valid warn ID (or "all"). you can see warn IDs of a user with `warnlist` command.'
            )

        # clears the warn with given id
        if warnId and isinstance(warnId, int):
            # trys to find if target user has the warn with given id or not
            row = await fetchone(
                f"""
                SELECT * FROM {WarnTable.TABLE_NAME}
                WHERE {WarnTable.COL_SERVER_ID} = ? AND {WarnTable.COL_USER_ID} = ? AND {WarnTable.COL_USER_WARN_ID} = ?;
                """,
                (ctx.guild.id, target.id, warnId),
            )
            # if no warn with given id is found, notifys the user
            if not row:
                return await ctx.reply(
                    f"{target.display_name} has no warning with that ID."
                )

            # deletes the warn with given id
            await execute(
                f"""
                DELETE FROM {WarnTable.TABLE_NAME}
                WHERE {WarnTable.COL_SERVER_ID} = ? AND {WarnTable.COL_USER_ID} = ? AND {WarnTable.COL_USER_WARN_ID} = ?;
                """,
                (ctx.guild.id, target.id, warnId),
            )

            await ctx.reply(
                f"{target.mention}'s warning with ID {warnId} has been cleared."
                + (f"\nreason: {reason}" if reason else "")
            )

        # clears all warns of the target
        else:
            # trys to find if target user has any warn or not
            row = await fetchall(
                f"""
                SELECT * FROM {WarnTable.TABLE_NAME}
                WHERE {WarnTable.COL_SERVER_ID} = ? AND {WarnTable.COL_USER_ID} = ?;
                """,
                (ctx.guild.id, target.id),
            )
            # if the target has no warn, notifys the user
            if not row:
                return await ctx.reply(f"{target.display_name} has no warning.")

            # deletes all warns
            await execute(
                f"""
                DELETE FROM {WarnTable.TABLE_NAME}
                WHERE {WarnTable.COL_SERVER_ID} = ? AND {WarnTable.COL_USER_ID} = ?;
                """,
                (ctx.guild.id, target.id),
            )

            await ctx.reply(
                f"{target.mention}'s warnings have been cleared."
                + (f"\nreason: {reason}" if reason else "")
            )

    @warnclear.error
    async def warnclear_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ):
        # if user entered an invalid user
        if isinstance(error, commands.BadArgument):
            await ctx.reply("User not found. Please mention a valid user.")
        else:
            logger.exception(f"❌ something went wrong with warnclear command:")
            await ctx.reply("something went wrong with **warnclear**.")

    # warnclear slash command
    @app_commands.command(name="warnclear", description=Help.brief, extras=Help.extras)
    @app_commands.guild_only()
    @app_commands.describe(
        user="The target user to clear it's warning.",
        warn_id="The ID of warning to clear.",
        reason="The reason to clear warning.",
    )
    async def slashWarnclear(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        warn_id: int | None = None,
        reason: str | None = None,
    ):
        # if user runs the command in dm
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You can only run moderation commands in a server.", ephemeral=True
            )

        # if the user has no permission to clear warns
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message(
                "You have no permission to *clear* Members' warnings.", ephemeral=True
            )

        # if the bot has no permission to clear warns
        if not interaction.guild.me.guild_permissions.kick_members:
            return await interaction.response.send_message(
                "I have no permisson to *clear* Members' warnings.", ephemeral=True
            )

        # if user wants to clear its own warns
        if user.id == interaction.user.id:
            return await interaction.response.send_message(
                "You can't clear your own warnings.", ephemeral=True
            )

        # if user wants to clear warns of the server owner
        if user.id == interaction.guild.owner_id:
            return await interaction.response.send_message(
                "Server *Owner* has no warning for you to remove it now.",
                ephemeral=True,
            )

        # if user wants to run moderation command on the bot
        if user.id == interaction.client.application_id:
            return await interaction.response.send_message(
                "I have no warning for you to remove it now??.", ephemeral=True
            )

        # if user wants to clear warns of bots
        if user.bot:
            return await interaction.response.send_message(
                "Bots have no warning for you to remove it now.", ephemeral=True
            )

        # if user has lower or equal role position than target
        if (
            user.top_role >= interaction.user.top_role
            and interaction.user.id != interaction.guild.owner_id
        ):
            return await interaction.response.send_message(
                "You can't clear warn of a Member with *higher or equal* role position as you.",
                ephemeral=True,
            )

        # if the bot has lower or equal role position than target
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                "I can't clear warn of a Member with *higher or equal* role position as me.",
                ephemeral=True,
            )

        # clears the warn with given id
        if warn_id:
            # trys to find if target user has the warn with given id or not
            row = await fetchone(
                f"""
                SELECT * FROM {WarnTable.TABLE_NAME}
                WHERE {WarnTable.COL_SERVER_ID} = ? AND {WarnTable.COL_USER_ID} = ? AND {WarnTable.COL_USER_WARN_ID} = ?;
                """,
                (interaction.guild.id, user.id, warn_id),
            )
            # if no warn with given id is found, notifys the user
            if not row:
                return await interaction.response.send_message(
                    f"{user.display_name} has no warning with that ID.", ephemeral=True
                )

            # deletes the warn with given id
            await execute(
                f"""
                DELETE FROM {WarnTable.TABLE_NAME}
                WHERE {WarnTable.COL_SERVER_ID} = ? AND {WarnTable.COL_USER_ID} = ? AND {WarnTable.COL_USER_WARN_ID} = ?;
                """,
                (interaction.guild.id, user.id, warn_id),
            )

            await interaction.response.send_message(
                f"{user.mention}'s warning with ID {warn_id} has been cleared."
                + (f"\nreason: {reason}" if reason else "")
            )

        # clears all warns of the target
        else:
            # trys to find if target user has any warn or not
            row = await fetchone(
                f"""
                SELECT * FROM {WarnTable.TABLE_NAME}
                WHERE {WarnTable.COL_SERVER_ID} = ? AND {WarnTable.COL_USER_ID} = ?;
                """,
                (interaction.guild.id, user.id),
            )
            # if the target has no warn, notifys the user
            if not row:
                return await interaction.response.send_message(
                    f"{user.display_name} has no warning.", ephemeral=True
                )

            # deletes all warns
            await execute(
                f"""
                DELETE FROM {WarnTable.TABLE_NAME}
                WHERE {WarnTable.COL_SERVER_ID} = ? AND {WarnTable.COL_USER_ID} = ?;
                """,
                (interaction.guild.id, user.id),
            )

            await interaction.response.send_message(
                f"{user.mention}'s warnings have been cleared."
                + (f"\nreason: {reason}" if reason else "")
            )

    @slashWarnclear.error
    async def slashWarnclear_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        logger.exception(f"❌ something went wrong with /warnclear command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **warnclear**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **warnclear**.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(WarnClear(bot))
