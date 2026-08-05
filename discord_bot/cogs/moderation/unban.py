import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class Unban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Moderation,
        is_dm_only=False,
        is_server_only=True,
        subcommands=None,
        permissions=["`Ban Members`"],
        help_=None,
        brief="Unbans a user from the server.",
        usage="<target_ID> <reason[*optional*]>",
        aliases=["ub"],
    )

    @commands.command(name="unban", **Help.to_kwargs)
    async def unban(
        self,
        ctx: commands.Context[commands.Bot],
        userId: int | str | None,
        *,
        reason: str | None = None,
    ):
        # if user runs the command in dm
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return await ctx.reply("You can only run moderation commands in a server.")

        # if the user has no permission to unban
        if not ctx.author.guild_permissions.ban_members:
            return await ctx.reply("You have no permission to *unban* Members.")

        # if the bot has no permission to unban
        if not ctx.guild.me.guild_permissions.ban_members:
            return await ctx.reply("I have no permisson to *unban* Members.")

        # if user doesn't enter any target ID
        if not userId:
            return await ctx.reply("You must enter a target user ID for this command.")

        # if user enters an invalid argument
        if not isinstance(userId, int):
            return await ctx.reply("You must enter a valid target user ID.")

        try:
            target = self.bot.get_user(userId) or await self.bot.fetch_user(
                userId
            )  # fetches the user from id
        except discord.NotFound:
            return await ctx.reply(f"User with this ID doesn't exist.")

        # if user wants to unban himself
        if target.id == ctx.author.id:
            return await ctx.reply("You were never banned for you to undo it now.")

        # if user trys to kick the server owner
        if target.id == ctx.guild.owner_id:
            return await ctx.reply(
                "The server *Owner* was never (and couldn't be) banned for you to undo it now."
            )

        # if user wants to do moderation command on the bot
        if target.id == ctx.me.id:
            return await ctx.reply(
                "If i'm texting you rn, that means I wasn't banned I guess?"
            )

        # unbans the target
        try:
            entry = await ctx.guild.fetch_ban(
                discord.Object(id=target.id)
            )  # checks if the target is banned
            await ctx.guild.unban(user=entry.user, reason=reason)
            await ctx.reply(
                f"{target.display_name} has been *unbanned* via {ctx.author.display_name}."
                + (f"\nreason: {reason}" if reason else "")
            )
        except discord.NotFound:
            return await ctx.reply(
                f"{target.display_name} was never banned for you to undo it now."
            )
        except Exception:
            logger.exception(f".unban failed to unban:")
            await ctx.reply("Failed to unban.")

    @unban.error
    async def unban_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ):
        logger.exception(f"❌ something went wrong with unban command:")
        await ctx.reply("something went wrong with **unban**.")

    # unban slash command
    @app_commands.command(name="unban", description=Help.brief, extras=Help.extras)
    @app_commands.guild_only()
    @app_commands.describe(
        user_id="The target user ID to unban.",
        reason="The reason you want to unban the target.",
    )
    async def slashUnban(
        self, interaction: discord.Interaction, user_id: int, reason: str | None = None
    ):
        # if user runs the command in dm
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You can only run moderation commands in a server.", ephemeral=True
            )

        # if the user has no permission to unban
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message(
                "You have no permission to *unban* Members.", ephemeral=True
            )

        # if the bot has no permission to unban
        if not interaction.guild.me.guild_permissions.ban_members:
            return await interaction.response.send_message(
                "I have no permisson to *unban* Members.", ephemeral=True
            )

        try:
            target = self.bot.get_user(user_id) or await self.bot.fetch_user(
                user_id
            )  # fetches the user from id
        except discord.NotFound:
            return await interaction.response.send_message(
                f"User with this ID doesn't exist.", ephemeral=True
            )

        # if user wants to unban himself
        if target.id == interaction.user.id:
            return await interaction.response.send_message(
                "You were never banned for you to undo it now.", ephemeral=True
            )

        # if user trys to unban the server owner
        if target.id == interaction.guild.owner_id:
            return await interaction.response.send_message(
                "The server *Owner* was never (and couldn't be) banned for you to undo it now.",
                ephemeral=True,
            )

        # if user wants to do moderation command on the bot
        if target.id == interaction.client.application_id:
            return await interaction.response.send_message(
                "If I'm texting you rn, that means I wasn't banned I guess?",
                ephemeral=True,
            )

        # unbans the target
        try:
            entry = await interaction.guild.fetch_ban(
                discord.Object(id=target.id)
            )  # checks if the target is banned
            await interaction.guild.unban(user=entry.user, reason=reason)
            await interaction.response.send_message(
                f"{target.display_name} has been *unbanned* via {interaction.user.display_name}."
                + (f"\nreason: {reason}" if reason else "")
            )
        except discord.NotFound:
            return await interaction.response.send_message(
                f"{target.display_name} was never banned for you to undo it now.",
                ephemeral=True,
            )
        except Exception:
            logger.exception(f".unban failed to unban:")
            await interaction.response.send_message("Failed to unban.", ephemeral=True)

    @slashUnban.error
    async def slashUnban_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        logger.exception(f"❌ something went wrong with /unban command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **unban**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **unban**.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Unban(bot))
