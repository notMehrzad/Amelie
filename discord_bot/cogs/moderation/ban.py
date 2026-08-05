import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class Ban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Moderation,
        is_dm_only=False,
        is_server_only=True,
        subcommands=None,
        permissions=["`Ban Members`"],
        help_=None,
        brief="Bans a member from the server.",
        usage="<target> <reason[*optional*]>",
        aliases=["b"],
    )

    @commands.command(name="ban", **Help.to_kwargs)
    async def ban(
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.User | int | str | None,
        *,
        reason: str | None = None,
    ):
        # if user runs the command in dm
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return await ctx.reply("You can only run moderation commands in a server.")

        # if the user has no permission to ban
        if not ctx.author.guild_permissions.ban_members:
            return await ctx.reply("You have no permission to *ban* Members.")

        # if the bot has no permission to ban
        if not ctx.guild.me.guild_permissions.ban_members:
            return await ctx.reply("I have no permisson to *ban* Members.")

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
            # if the target is not a member and is in the ban list
            try:
                await ctx.guild.fetch_ban(discord.Object(id=user.id))
                await ctx.reply(f"{user.display_name} is banned already.")
                return
            except discord.NotFound:
                return await ctx.reply(
                    f"{user.display_name} is not a Member of this server."
                )

        # if user wants to ban himself
        if target.id == ctx.author.id:
            return await ctx.reply("You can't ban yourself.")

        # if user trys to ban the server owner
        if target.id == ctx.guild.owner_id:
            return await ctx.reply("You can't ban the server *Owner*.")

        # if user wants to run moderation command on the bot
        if target.id == ctx.me.id:
            return await ctx.reply(
                "You can't run my moderation commands on myself.\nnice try."
            )

        # if user has lower or equal role position than target
        if (
            target.top_role >= ctx.author.top_role
            and ctx.author.id != ctx.guild.owner_id
        ):
            return await ctx.reply(
                "You can't ban a Member with *higher or equal* role position as you."
            )

        # if the bot has lower or equal role position than target
        if target.top_role >= ctx.guild.me.top_role:
            return await ctx.reply(
                "I can't ban a Member with *higher or equal* role position as me."
            )

        # bans the target
        try:
            await ctx.guild.ban(user=target, reason=reason)
            await ctx.reply(
                f"{target.display_name} has been *banned* via {ctx.author.display_name}."
                + (f"\nreason: {reason}" if reason else "")
            )
        except Exception:
            logger.exception(f".ban failed to ban:")
            await ctx.reply("Failed to ban.")

    @ban.error
    async def ban_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ):
        # if user entered an invalid user
        if isinstance(error, commands.BadArgument):
            await ctx.reply("Member not found. Please mention a valid member.")
        else:
            logger.exception(f"❌ something went wrong with ban command:")
            await ctx.reply("something went wrong with **ban**.")

    # ban slash command
    @app_commands.command(name="ban", description=Help.brief, extras=Help.extras)
    @app_commands.guild_only()
    @app_commands.describe(
        user="The target Member to ban from the server.",
        reason="The reason you want to ban the target.",
    )
    async def slashBan(
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

        # if the user has no permission to ban
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message(
                "You have no permission to *ban* Members.", ephemeral=True
            )

        # if the bot has no permission to ban
        if not interaction.guild.me.guild_permissions.ban_members:
            return await interaction.response.send_message(
                "I have no permisson to *ban* Members.", ephemeral=True
            )

        # if user wants to ban himself
        if user.id == interaction.user.id:
            return await interaction.response.send_message(
                "You can't ban yourself.", ephemeral=True
            )

        # if user trys to ban the server owner
        if user.id == interaction.guild.owner_id:
            return await interaction.response.send_message(
                "You can't ban the server *Owner*.", ephemeral=True
            )

        # if user wants to run moderation command on the bot
        if user.id == interaction.client.application_id:
            return await interaction.response.send_message(
                "You can't run my moderation commands on myself.\nnice try.",
                ephemeral=True,
            )

        # if user has lower or equal role position than target
        if (
            user.top_role >= interaction.user.top_role
            and interaction.user.id != interaction.guild.owner_id
        ):
            return await interaction.response.send_message(
                "You can't ban a Member with *higher or equal* role position as you.",
                ephemeral=True,
            )

        # if the bot has lower or equal role position than target
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                "I can't ban a Member with *higher or equal* role position as me.",
                ephemeral=True,
            )

        # bans the target
        try:
            await interaction.guild.ban(user=user, reason=reason)
            await interaction.response.send_message(
                f"{user.display_name} has been *banned* via {interaction.user.display_name}."
                + (f"\nreason: {reason}" if reason else "")
            )
        except Exception:
            logger.exception(f".ban failed to ban:")
            await interaction.response.send_message("Failed to ban.", ephemeral=True)

    @slashBan.error
    async def slashBan_error(self, interaction: discord.Interaction, error: Exception):
        logger.exception(f"❌ something went wrong with /ban command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **ban**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **ban**.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Ban(bot))
