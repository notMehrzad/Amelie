import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class Whisper(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Utility,
        is_dm_only=False,
        is_server_only=True,
        subcommands=None,
        permissions=None,
        help_="Whispers a message to a member. use this command to talk with a member privately inside a server.",
        brief="Whispers something to a member.",
        usage="<target> <message>",
        aliases=["wh"],
    )

    @commands.command(name="whisper", **Help.to_kwargs)
    async def whisper(
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.User | str | None,
        *,
        message: str | None,
    ):
        # if user runs the command in dm
        if not ctx.guild:
            return await ctx.reply("You can only whisper someone in a server.")

        # if user doesn't enter a target user
        if not user:
            return await ctx.reply("You must mention a Member to whisper.")

        # if user mentions an invalid user
        if not isinstance(user, discord.abc.User):
            raise commands.BadArgument

        target = ctx.guild.get_member(
            user.id
        )  # fetches the target user from the server, None if not found
        if not target:
            return await ctx.reply(
                f"{user.display_name} is not a member of this server."
            )

        # if user target is user himself
        if target.id == ctx.author.id:
            return await ctx.reply("You can't whisper to yourself.")

        # if target user is a bot except the bot itself
        if target.bot and target.id != ctx.me.id:
            return await ctx.reply("You can't whisper to dumb bots. (except me ofc)")

        if not message:
            return await ctx.reply("You must write your message to be whispered.")

        await ctx.message.delete()  # deletes the users message

        # the bot responds if target is the bot
        if target.id == ctx.me.id:
            return await ctx.reply("I hear your words..")

        view = WhisperView(ctx, ctx.author, target, message)  # initializes the view
        await view.start()  # starts the view

    @whisper.error
    async def whisper_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ):
        # if user mentioned an invalid user
        if isinstance(error, commands.BadArgument):
            await ctx.reply("user not found. Please mention a valid member.")
        else:
            logger.exception(f"❌ something went wrong with whisper command:")
            await ctx.reply("something went wrong with **whisper**.")

    # whisper slash command
    @app_commands.command(name="whisper", description=Help.brief, extras=Help.extras)
    @app_commands.guild_only()
    @app_commands.describe(
        target="The Member to whisper.", message="The message to be whispered."
    )
    async def slashWhisper(
        self, interaction: discord.Interaction, target: discord.Member, message: str
    ):
        # if user target is user himself
        if target.id == interaction.user.id:
            return await interaction.response.send_message(
                "You can't whisper to yourself.", ephemeral=True
            )

        # the bot responds if target is the bot
        if target.id == interaction.application_id:
            return await interaction.response.send_message(
                "I hear your words..", ephemeral=True
            )

        # if target user is a bot except the bot itself
        if target.bot:
            return await interaction.response.send_message(
                "You can't whisper to dumb bots. (except me ofc)", ephemeral=True
            )

        view = WhisperView(
            interaction, interaction.user, target, message
        )  # initializes the view
        await view.start()  # starts the view

    @slashWhisper.error
    async def slashWhisper_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        logger.exception(f"❌ something went wrong with /whisper command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **whisper**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **whisper**.", ephemeral=True
            )


class WhisperView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        user: discord.abc.User,
        target: discord.Member,
        msg: str,
    ):
        super().__init__(timeout=300)
        if isinstance(ctx, discord.Interaction):
            self.slash = True
            self.interaction = ctx
        else:
            self.slash = False
            self.ctx = ctx
        self.user = user
        self.target = target
        self.msg = msg

    async def start(self):
        desc = f"{self.target.mention}, You have a whisper from {self.user.mention}."
        if not self.slash:
            self.ctxMsg = await self.ctx.send(content=desc, view=self)
        else:
            if isinstance(self.interaction.channel, discord.TextChannel):
                await self.interaction.response.defer(ephemeral=True)
                self.ctxMsg = await self.interaction.channel.send(
                    content=desc, view=self
                )
                await self.interaction.edit_original_response(
                    content="Whisper has been sent."
                )

    # defines read button
    @discord.ui.button(label="read", style=discord.ButtonStyle.grey)
    async def read(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ):
        if interaction.user.id not in (self.target.id, self.user.id):
            return await interaction.response.send_message(
                "You can't read others whisper.", ephemeral=True
            )

        # if user trys to read his own whisper
        if interaction.user.id == self.user.id:
            return await interaction.response.send_message(
                f"*You whisper to {self.target.mention}:*\n{self.msg}", ephemeral=True
            )

        await interaction.response.send_message(
            f"*{self.user.display_name} whispers to you:*\n{self.msg}", ephemeral=True
        )  # shows whisper to the target

        finalEmbed = discord.Embed(
            title="whisper",
            description=f"{self.target.display_name} has read the whisper from {self.user.display_name}.",
        )
        await self.ctxMsg.edit(
            content=None, embed=finalEmbed, view=None
        )  # edits the sent message to show the reading status

        self.stop()  # stops the view after target has read the whisper

    async def on_timeout(self):
        self.read.disabled = True

        toEmbed = discord.Embed(
            title="whisper",
            description=f"⏰ The whisper got forgotten.. {self.target.display_name} didn't get it early.",
        )
        try:
            await self.ctxMsg.edit(embed=toEmbed, view=self)
        except discord.NotFound:
            pass

        self.stop()

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ):
        logger.exception(
            f"❌ something went wrong with whisper interaction - button: {getattr(item, 'label', 'unknown')}"
        )
        try:
            await interaction.response.send_message(
                "something went wrong with **whisper**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **whisper**.", ephemeral=True
            )
        except Exception:
            pass

        self.stop()  # stops further interaction


async def setup(bot: commands.Bot):
    await bot.add_cog(Whisper(bot))
