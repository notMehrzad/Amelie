import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class Kick(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Moderation,
        is_dm_only=False,
        is_server_only=True,
        subcommands=None,
        permissions=["`Kick, Approve and Reject Members`"],
        help_=None,
        brief="Kicks a member from the server.",
        usage="<target> <reason[*optional*]>",
        aliases=["k"],
    )

    @commands.command(name="kick", **Help.to_kwargs)
    async def kick(
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.User | int | str | None,
        *,
        reason: str | None = None,
    ):
        # if user runs the command in dm
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return await ctx.reply("You can only run moderation commands in a server.")

        # if the user has no permission to kick
        if not ctx.author.guild_permissions.kick_members:
            return await ctx.reply("You have no permission to *kick* Members.")

        # if the bot has no permission to kick
        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.reply("I have no permisson to *kick* Members.")

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

        # if user wants to kick himself
        if target.id == ctx.author.id:
            return await ctx.reply("You can't kick yourself!")

        # if user trys to kick the server owner
        if target.id == ctx.guild.owner_id:
            return await ctx.reply("You can't kick the server *Owner*.")

        # if user wants to run moderation command on the bot
        if target.id == ctx.me.id:
            return await ctx.reply(
                "You can't run my moderation commands on myself darling."
            )

        # if user has lower or equal role position than target
        if (
            target.top_role >= ctx.author.top_role
            and ctx.author.id != ctx.guild.owner_id
        ):
            return await ctx.reply(
                "You can't kick a Member with *higher or equal* role position as you."
            )

        # if the bot has lower or equal role position than target
        if target.top_role >= ctx.guild.me.top_role:
            return await ctx.reply(
                "I can't kick a Member with *higher or equal* role position as me."
            )

        # kicks the target
        try:
            await ctx.guild.kick(user=target, reason=reason)
            await ctx.reply(
                f"{target.display_name} has been *kicked* via {ctx.author.display_name}."
                + (f"\nreason: {reason}" if reason else "")
            )
        except Exception:
            logger.exception(f".kick failed to kick:")
            await ctx.reply("Failed to kick.")

    @kick.error
    async def kick_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ):
        # if user entered an invalid user
        if isinstance(error, commands.BadArgument):
            await ctx.reply("Member not found. Please mention a valid member.")
        else:
            logger.exception(f"❌ something went wrong with kick command:")
            await ctx.reply("something went wrong with **kick**.")

    # kick slash command
    @app_commands.command(name="kick", description=Help.brief, extras=Help.extras)
    @app_commands.guild_only()
    @app_commands.describe(
        user="The target Member to kick from the server.",
        reason="The reason you want to kick the target.",
    )
    async def slashKick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str | None = None,
    ):
        # if user runs the command in dm
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You can only run moderation commands in a server.", ephemeral=True
            )

        # if the user has no permission to kick
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message(
                "You have no permission to *kick* Members.", ephemeral=True
            )

        # if the bot has no permission to kick
        if not interaction.guild.me.guild_permissions.kick_members:
            return await interaction.response.send_message(
                "I have no permisson to *kick* Members.", ephemeral=True
            )

        # if user wants to kick himself
        if user.id == interaction.user.id:
            return await interaction.response.send_message(
                "You can't kick yourself!", ephemeral=True
            )

        # if user trys to kick the server owner
        if user.id == interaction.guild.owner_id:
            return await interaction.response.send_message(
                "You can't kick the server *Owner*.", ephemeral=True
            )

        # if user wants to run moderation command on the bot
        if user.id == interaction.client.application_id:
            return await interaction.response.send_message(
                "You can't run my moderation commands on myself darling.",
                ephemeral=True,
            )

        # if user has lower or equal role position than target
        if (
            user.top_role >= interaction.user.top_role
            and interaction.user.id != interaction.guild.owner_id
        ):
            return await interaction.response.send_message(
                "You can't kick a Member with *higher or equal* role position as you.",
                ephemeral=True,
            )

        # if the bot has lower or equal role position than target
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                "I can't kick a Member with *higher or equal* role position as me.",
                ephemeral=True,
            )

        # kicks the target
        try:
            await interaction.guild.kick(user=user, reason=reason)
            await interaction.response.send_message(
                f"{user.display_name} has been *kicked* via {interaction.user.display_name}."
                + (f"\nreason: {reason}" if reason else "")
            )
        except Exception:
            logger.exception(f".kick failed to kick:")
            await interaction.response.send_message("Failed to kick.", ephemeral=True)

    @slashKick.error
    async def slashKick_error(self, interaction: discord.Interaction, error: Exception):
        logger.exception(f"❌ something went wrong with /kick command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **kick**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **kick**.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Kick(bot))
