import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.database import fetchall, fetchone
from core.dbconstants import AnonymousContactTable, AnonymousUserTable
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class AnonBlockList(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Anonymous,
        is_dm_only=True,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=(
            "Shows the Anonymous block list of the user."
            "\n\nEvery each blocked Anonymous sender private ID will be listed."
        ),
        brief="Shows the Anonymous block list.",
        usage=None,
        aliases=["anonbl"],
    )

    @commands.command(name="anonblocklist", **Help.to_kwargs)
    async def anonblocklist(self, ctx: commands.Context[commands.Bot]):
        # if user runs the command in a server
        if ctx.guild:
            return await ctx.reply("This command can only be used in Amélie's dm.")

        # checks if the user has a public id
        row = await fetchone(
            f"""
            SELECT {AnonymousUserTable.COL_PUBLIC_ID} FROM {AnonymousUserTable.TABLE_NAME}
            WHERE {AnonymousUserTable.COL_USER_ID} = ?;
            """,
            (ctx.author.id,),
        )
        if not row:
            return await ctx.reply(
                "You have no public ID which means you have no block list either."
            )

        # fetches all blocked users
        rows = await fetchall(
            f"""
            SELECT {AnonymousContactTable.COL_ALIAS} FROM {AnonymousContactTable.TABLE_NAME}
            WHERE {AnonymousContactTable.COL_RECIPIENT_ID} = ? AND {AnonymousContactTable.COL_IS_BLOCKED} = ?;
            """,
            (ctx.author.id, 1),
        )
        # if no user was blocked, notifies the user
        if not row:
            return await ctx.reply("Your block list is empty.")

        # sends the result
        resultEmbed = discord.Embed(
            title="Anonymous Block List",
            description="\n".join(
                f"{i}. {row['contact_anon_id']}" for i, row in enumerate(rows, start=1)
            ),
            color=discord.Color.blurple(),
        )
        await ctx.reply(embed=resultEmbed)

    @anonblocklist.error
    async def anonblocklist_error(
        self, ctx: commands.Context[commands.Bot], error: Exception
    ):
        logger.exception(f"❌ something went wrong with anonblocklist command:")
        await ctx.reply("something went wrong with **anonblocklist**.")

    # anonblocklist slash command
    @app_commands.command(
        name="anonblocklist", description=Help.brief, extras=Help.extras
    )
    @app_commands.dm_only()
    async def slashAnonblocklist(self, interaction: discord.Interaction):
        # checks if the user has a public id
        row = await fetchone(
            f"""
            SELECT {AnonymousUserTable.COL_PUBLIC_ID} FROM {AnonymousUserTable.TABLE_NAME}
            WHERE {AnonymousUserTable.COL_USER_ID} = ?;
            """,
            (interaction.user.id,),
        )
        if not row:
            return await interaction.response.send_message(
                "You have no public ID which means you have no block list either.",
                ephemeral=True,
            )

        # fetches all blocked users
        rows = await fetchall(
            f"""
            SELECT {AnonymousContactTable.COL_ALIAS} FROM {AnonymousContactTable.TABLE_NAME}
            WHERE {AnonymousContactTable.COL_RECIPIENT_ID} = ? AND {AnonymousContactTable.COL_IS_BLOCKED} = ?;
            """,
            (interaction.user.id, 1),
        )
        # if no user was blocked, notifies the user
        if not row:
            return await interaction.response.send_message(
                "Your block list is empty.", ephemeral=True
            )

        # sends the result
        resultEmbed = discord.Embed(
            title="Anonymous Block List",
            description="\n".join(
                f"{i}. {row['contact_anon_id']}" for i, row in enumerate(rows, start=1)
            ),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=resultEmbed)

    @slashAnonblocklist.error
    async def slashAnonblocklist_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        logger.exception(f"❌ something went wrong with /anonblocklist command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **anonblocklist**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **anonblocklist**.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(AnonBlockList(bot))
