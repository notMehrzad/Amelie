import random

import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class Choice:
    def __init__(self, name: str, beats: str, emoji: str):
        self.name = name
        self.beats = beats
        self.emoji = emoji


Rock = Choice("Rock", "Scissors", "<:susrock:1013833657749864529>")
Paper = Choice("Paper", "Rock", "📃")
Scissors = Choice("Scissors", "Paper", "✂️")
choices = (Rock, Paper, Scissors)


def rpsResult(
    c1: tuple[discord.abc.User, Choice], c2: tuple[discord.abc.User, Choice]
) -> discord.abc.User | None:
    """
    Checks the result of a Rock, Paper, Scissors match.

    Parameters
    ---------
    c1: tuple[:class:`discord.abc.User`, :class:`Choice`]
        The first player's user instance and played option wrapped inside a tuple.
    c2: tuple[:class:`discord.abc.User`, :class:`Choice`]
        The second player's user instance and played option wrapped inside a tuple.

    Returns
    -------
    :class:`discord.abc.User`
        The winner user instance.
    ``None``
        If the result is a draw.
    """

    # draw
    if c1[1].name == c2[1].name:
        return None
    # player 2 wins
    elif c2[1].beats == c1[1].name:
        return c2[0]
    # player 1 wins
    else:
        return c1[0]


class Rps(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Games,
        is_dm_only=False,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=(
            "A game between two people. Both players play one of three options: Rock, Paper or Scissors."
            "\n\nA Rock beats Scissors, a Paper beats Rock, a Scissors beats Paper."
            "\n\nYou can only play with Amélie herself if you run this game in her dm."
        ),
        brief="Traditional *Rock, Paper, Scissors* game.",
        usage="<target[*optional*]>",
        aliases=["rockpaperscissors"],
    )

    @commands.command(name="rps", **Help.to_kwargs)
    async def rps(
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.User | str | None = None,
    ):
        # if user mentions a target
        if user:
            # if the target is invalid
            if not isinstance(user, discord.abc.User):
                return await ctx.reply("Mention a valid user.")

            # if the target is user themselves
            if user.id == ctx.author.id:
                return await ctx.reply("You can't play with yourself.")

            # if user runs the command in dm and target is not the bot
            if not ctx.guild and user.id != ctx.me.id:
                return await ctx.reply(
                    "You can play this game with others only in a server they are also in."
                )

            if user and ctx.guild:
                target = ctx.guild.get_member(user.id)
                if not target:
                    return await ctx.reply(
                        f"{user.mention} is not a member of this server."
                    )
            else:
                target = None

            # if user wants to play with any other bot
            if user.bot and user.id != ctx.me.id:
                return await ctx.reply("You can't play with bots. (except me!)")

            # if target is bot, bot plays
            if user.id == ctx.me.id:
                target = None

            # trys to fetch the taget user otherwise
            else:
                target = ctx.guild.get_member(user.id) if ctx.guild else None
                if not target:
                    return await ctx.reply(
                        f"{user.mention} is not a member of this server."
                    )

        else:
            target = None

        view = RpsView(ctx, target) if target else RpsView(ctx, ctx.me, botPlay=True)
        await view.start()

    @rps.error
    async def rps_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ):
        logger.exception(f"❌ something went wrong with rps command:")
        await ctx.reply("something went wrong with **rps**.")

    # rps slash command
    @app_commands.command(name="rps", description=Help.brief, extras=Help.extras)
    @app_commands.describe(user="The user you want to play rps with.")
    async def slashRps(
        self, interaction: discord.Interaction, user: discord.User | None = None
    ):
        # if user mentions a target
        if user:
            # if the target is user themselves
            if user.id == interaction.user.id:
                return await interaction.response.send_message(
                    "You can't play with yourself.", ephemeral=True
                )

            # if user runs the command in dm and target is not the bot
            if not interaction.guild and user.id != interaction.application_id:
                return await interaction.response.send_message(
                    "You can play this game with others only in a server they are also in.",
                    ephemeral=True,
                )

            if user and interaction.guild:
                target = interaction.guild.get_member(user.id)
                if not target:
                    return await interaction.response.send_message(
                        f"{user.mention} is not a member of this server.",
                        ephemeral=True,
                    )
            else:
                target = None

            # if user wants to play with any other bot
            if user.bot and user.id != interaction.application_id:
                return await interaction.response.send_message(
                    "You can't play with bots. (except me!)", ephemeral=True
                )

            # if target is bot, bot plays
            if user.id == interaction.application_id:
                target = None

            # trys to fetch the taget user otherwise
            else:
                target = (
                    interaction.guild.get_member(user.id) if interaction.guild else None
                )
                if not target:
                    return await interaction.response.send_message(
                        f"{user.mention} is not a member of this server.",
                        ephemeral=True,
                    )

        else:
            target = None

        if target:
            view = RpsView(interaction, target)
            await view.start()
        else:
            if isinstance(interaction.client.user, discord.abc.User):
                view = RpsView(interaction, interaction.client.user, botPlay=True)
                await view.start()

    @slashRps.error
    async def slashRps_error(self, interaction: discord.Interaction, error: Exception):
        logger.exception(f"❌ something went wrong with /rps command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **rps**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **rps**.", ephemeral=True
            )


class RpsView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        target: discord.abc.User,
        botPlay: bool = False,
    ):
        super().__init__(timeout=180)
        if isinstance(ctx, discord.Interaction):
            self.slash = True
            self.interaction = ctx
        else:
            self.slash = False
            self.ctx = ctx
        self.user = self.interaction.user if self.slash else self.ctx.author
        self.target = target
        self.botPlay = botPlay
        self.embedColor = discord.Color.random()
        self.timestamp = discord.utils.utcnow()
        self.userChoice: Choice | None = None
        self.targetChoice: Choice | None = None
        self.state = "target_choose"

        # creates buttons as many as given in choices list
        for choice in choices:
            button: discord.ui.Button[discord.ui.View] = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label=choice.name,
                emoji=choice.emoji,
            )
            button.callback = self.make_callback(choice)
            self.add_item(button)

    async def start(self):
        if self.botPlay:
            content = None
            desc = "*You wanna play with ME??\nsounds fine-\nlets start the game then.*"
        else:
            content = f"{self.target.mention}, You're challenged to a game of *Rock, Paper, Scissors !* by {self.user.mention}"  # notifies the target
            desc = f"It's currently {self.target.mention}'s turn to play."

        startEmbed = discord.Embed(
            title="Rock, Paper, Scissors !",
            description=desc,
            color=self.embedColor,
            timestamp=self.timestamp,
        )
        # sends the initial message
        if self.slash:
            await self.interaction.response.send_message(
                content=content, embed=startEmbed, view=self
            )
        else:
            self.msg = await self.ctx.send(
                content=content, embed=startEmbed, view=self
            )  # saves the message to edit later

    def make_callback(self, choice: Choice):
        async def callback(interaction: discord.Interaction):
            # checks if only the user and target can interact with buttons
            if interaction.user.id not in (self.target.id, self.user.id):
                return await interaction.response.send_message(
                    "You can't play in this match.", ephemeral=True
                )

            # if user trys to play when it's target's turn
            if (
                not self.botPlay
                and self.state == "target_choose"
                and interaction.user.id != self.target.id
            ):
                if not self.userChoice:
                    return await interaction.response.send_message(
                        f"It's currently {self.target.mention}'s turn to play.",
                        ephemeral=True,
                    )
                else:
                    return await interaction.response.send_message(
                        f"You've already played your turn. ({self.userChoice.emoji})",
                        ephemeral=True,
                    )

            # if target trys to play when it's user's turn
            if self.state == "user_choose" and interaction.user.id != self.user.id:
                if not self.targetChoice:
                    return await interaction.response.send_message(
                        f"It's currently {self.user.mention}'s turn to play.",
                        ephemeral=True,
                    )
                else:
                    return await interaction.response.send_message(
                        f"You've already played your turn. ({self.targetChoice.emoji})",
                        ephemeral=True,
                    )

            # if bot is the target
            if self.botPlay:
                self.targetChoice = random.choice(
                    choices
                )  # saves the choice for the bot
                self.state = "user_choose"  # bot's turn's over, user's turn starts

            # target's turn
            if self.state == "target_choose":
                self.targetChoice = choice  # saves the choice for the target

                await interaction.response.send_message(
                    f"You played {self.targetChoice.emoji}.", ephemeral=True
                )

                userchooseEmbed = discord.Embed(
                    title="Rock, Paper, Scissors !",
                    description=f"{self.target.mention} played their turn.\n\nIt's currently {self.user.mention}'s turn to play.",
                    color=self.embedColor,
                    timestamp=self.timestamp,
                )
                if self.slash:
                    await self.interaction.edit_original_response(
                        content=None, embed=userchooseEmbed
                    )
                    await self.interaction.followup.send(
                        f"{self.user.mention}, It's your turn now !"
                    )
                else:
                    await self.msg.edit(content=None, embed=userchooseEmbed)
                    await self.msg.reply(f"{self.user.mention}, It's your turn now !")

                self.state = "user_choose"  # target's turn's over, user's turn starts

            # user's turn
            elif self.state == "user_choose":
                self.userChoice = choice  # saves the choice for the user

                self.state = "result"  # result phase begins
                await self.endMatch()

        return callback

    async def endMatch(self):
        if self.targetChoice and self.userChoice:
            winner = rpsResult(
                (self.target, self.targetChoice),
                (self.user, self.userChoice),
            )  # gets the result

            # draw
            if not winner:
                desc = "**It was a Draw !**"
                cori = (
                    f"{self.user.mention} escaped this time." if self.botPlay else None
                )
            else:
                # target wins
                if winner.id == self.target.id:
                    desc = (
                        f"**{winner.mention} has Won !**"
                        if not self.botPlay
                        else "**I have Won !**"
                    )
                    cori = "huh. not even a single sweat-" if self.botPlay else None
                # user wins
                else:
                    desc = f"**{winner.mention} has Won !**"
                    cori = "-ahh. maybe another time." if self.botPlay else None

            resultEmbed = (
                discord
                .Embed(
                    title="Rock, Paper, Scissors ! ",
                    description=desc,
                    color=discord.Color.random(),
                    timestamp=self.timestamp,
                )
                .set_footer(text=cori)
                .add_field(
                    name=f"{self.user.display_name} Choice",
                    value=f"{self.userChoice.name} {self.userChoice.emoji}",
                    inline=True,
                )
                .add_field(
                    name=f"{self.target.display_name} Choice",
                    value=f"{self.targetChoice.name} {self.targetChoice.emoji}",
                    inline=True,
                )
                .set_thumbnail(url=winner.display_avatar.url if winner else None)
            )
            # sends the result
            if self.slash:
                await self.interaction.edit_original_response(
                    embed=resultEmbed, view=None
                )
            else:
                await self.msg.edit(embed=resultEmbed, view=None)

            self.stop()  # stops the view

    async def on_timeout(self):
        # disables buttons on timeout
        for btn in self.children:
            if isinstance(btn, discord.ui.Button):
                btn.disabled = True

        if self.botPlay:
            guiltyStr = f"{self.user.mention} didn't make a move.\n*shame on you..*"
        elif self.state == "target_choose":
            guiltyStr = f"{self.target.mention} didn't seem brave enough to accept the challenge."
        else:
            guiltyStr = (
                f"{self.user.mention} seemed to have more important buisness to do."
            )

        toEmbed = discord.Embed(
            title="Rock, Paper, Scissors !",
            description=f"⏰ The game has timed out! {guiltyStr}",
            color=discord.Color.dark_gray(),
            timestamp=self.timestamp,
        )
        try:
            # sends the timeout message
            if self.slash:
                await self.interaction.edit_original_response(
                    content=None, embed=toEmbed, view=self
                )
            else:
                await self.msg.edit(content=None, embed=toEmbed, view=self)
        # if context message is deleted
        except discord.NotFound:
            pass

        self.stop()  # stops the view upon timeout

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ):
        logger.exception(
            f"❌ something went wrong with rps interaction - button: {getattr(item, 'label', 'unknown')}"
        )
        try:
            await interaction.response.send_message(
                "something went wrong with **rps**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **rps**.", ephemeral=True
            )
        except Exception:
            pass

        self.stop()  # stops the view upon error


async def setup(bot: commands.Bot):
    await bot.add_cog(Rps(bot))
