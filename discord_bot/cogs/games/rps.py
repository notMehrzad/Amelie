"""rps command."""

from __future__ import annotations

__all__ = []

import secrets
from enum import Enum, auto
from typing import cast, final

import discord
from discord import app_commands
from discord.ext import commands

from core.help_data_constants import RPS_HELP
from core.log_handler import setup_logger
from core.rps import RPSGame, RPSOption

logger = setup_logger(__name__)


@final
class _RPSGameState(Enum):
    USER_CHOICE = auto()
    TARGET_CHOICE = auto()
    RESULT = auto()


@final
class Rps(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name=RPS_HELP.name, **RPS_HELP.kwargs)
    async def rps(
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.abc.User | str | None = None,
    ) -> None:
        # If user enters no target user.
        if user is None:
            target = ctx.me

        # If user enters a tarrget user.
        else:
            # Raise an error if user enters an invlaid target user.
            if not isinstance(user, discord.abc.User):
                await ctx.reply("Mention a valid user.")
                return

            # Raise an error if user wants to play with themselves.
            if user.id == ctx.author.id:
                await ctx.reply("You can't play with yourself.")
                return

            # Raise an error if user wants to play with a bot.
            if user.bot and user.id != ctx.me.id:
                await ctx.reply("You can't play with bots. (except me!)")
                return

            # If command is being invoked is DM.
            if ctx.guild is None:
                # Raise an error if user wants to play with anyone in DM.
                if user.id != ctx.me.id:
                    await ctx.reply(
                        "You can play this game with others only in a server they are"
                        " also in.",
                    )
                    return
                target = ctx.me

            # If command is being invoked in a guild
            elif user.id == ctx.me.id:
                target = ctx.me

            else:
                # Fetch the target user in the guild.
                target = ctx.guild.get_member(user.id)
                # Raise an error if the target user can't be fetched.
                if target is None:
                    await ctx.reply(
                        f"{user.mention} is not a member of this server.",
                    )
                    return

        # Start the view.
        await RpsView(ctx, target).start()

    @rps.error
    async def rps_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error("❌ Something went wrong with rps command:", exc_info=error)
        await ctx.reply("Something went wrong with **rps**.")

    # rps slash command
    @app_commands.command(
        name=RPS_HELP.name,
        description=RPS_HELP.brief,
        extras=RPS_HELP.extras,
    )
    @app_commands.describe(user="The user you want to play rps with.")
    async def slash_rps(
        self,
        interaction: discord.Interaction,
        user: discord.abc.User | None = None,
    ) -> None:
        client_user = cast("discord.user.ClientUser", interaction.client.user)
        # If user enters no target user.
        if user is None:
            target = client_user

        # If user enters a tarrget user.
        else:
            # Raise an error if user wants to play with themselves.
            if user.id == interaction.application_id:
                await interaction.response.send_message(
                    "You can't play with yourself.",
                    ephemeral=True,
                )
                return

            # Raise an error if user wants to play with a bot.
            if user.bot and user.id != interaction.application_id:
                await interaction.response.send_message(
                    "You can't play with bots. (except me!)",
                    ephemeral=True,
                )
                return

            # If command is being invoked is DM.
            if interaction.guild is None:
                # Raise an error if user wants to play with anyone in DM.
                if user.id != interaction.application_id:
                    await interaction.response.send_message(
                        "You can play this game with others only in a server they are"
                        " also in.",
                        ephemeral=True,
                    )
                    return
                target = client_user

            # If command is being invoked in a guild
            elif user.id == interaction.application_id:
                target = client_user

            else:
                # Fetch the target user in the guild.
                target = interaction.guild.get_member(user.id)
                # Raise an error if the target user can't be fetched.
                if target is None:
                    await interaction.response.send_message(
                        f"{user.mention} is not a member of this server.",
                        ephemeral=True,
                    )
                    return

        # Start the view.
        await RpsView(interaction, target).start()

    @slash_rps.error
    async def slash_rps_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        logger.error("❌ Something went wrong with /rps command:", exc_info=error)
        try:
            await interaction.response.send_message(
                "Something went wrong with **rps**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **rps**.",
                ephemeral=True,
            )


class RpsView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        target: discord.abc.User,
    ) -> None:
        super().__init__(timeout=180)
        if isinstance(ctx, discord.Interaction):
            self.slash_command = True
            self.interaction = ctx
            self.user = self.interaction.user
            if self.target.id == self.interaction.application_id:
                self.bot_plays = True
            else:
                self.bot_plays = False
        else:
            self.slash_command = False
            self.ctx = ctx
            self.user = self.ctx.author
            if self.target.id == self.ctx.me.id:
                self.bot_plays = True
            else:
                self.bot_plays = False
        self.target: discord.abc.User = target

        self.game = RPSGame(self.user.id, self.target.id)
        self.state: _RPSGameState = _RPSGameState.TARGET_CHOICE

        self.embed_color = discord.Color.random()
        self.timestamp = discord.utils.utcnow()

        # Create as mnay buttons as options for RPS.
        for option in RPSOption:
            button: discord.ui.Button[discord.ui.View] = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label=option.name,
                emoji=option.emoji,
            )
            button.callback = self._make_callback(option)
            self.add_item(button)

    def play_bot_turn(self) -> None:
        """Play bot's turn.

        Bot picks a random RPS option.
        """
        self.game.player2_plays(secrets.choice(list(RPSOption)))
        self.state = _RPSGameState.USER_CHOICE

    async def start(self) -> None:
        """Start the view."""
        if self.bot_plays:
            self.play_bot_turn()

            content = None
            desc = "*You wanna play with ME??\nsounds fine-\nlets start the game then.*"
        else:
            content = (
                f"{self.target.mention}, You're challenged to a game of"
                " *Rock, Paper, Scissors !* by {self.user.mention}"
            )
            desc = f"It's currently {self.target.mention}'s turn to play."

        initial_embed = discord.Embed(
            color=self.embed_color,
            title="Rock, Paper, Scissors !",
            description=desc,
            timestamp=self.timestamp,
        )
        # Send initial embed.
        if self.slash_command:
            await self.interaction.response.send_message(
                content=content,
                embed=initial_embed,
                view=self,
            )
        else:
            self.msg = await self.ctx.send(
                content=content,
                embed=initial_embed,
                view=self,
            )

    def _make_callback(  # noqa: ANN202
        self,
        rps_option: RPSOption,
    ):
        async def callback(interaction: discord.Interaction) -> None:
            # Raise an error if interaction is not from user or target.
            if interaction.user.id not in (self.target.id, self.user.id):
                await interaction.response.send_message(
                    "You can't play in this game.",
                    ephemeral=True,
                )
                return

            # Raise an error if it's target's turn and interaction is from user.
            if (
                self.state == _RPSGameState.TARGET_CHOICE
                and interaction.user.id != self.target.id
            ):
                if self.game.player1_choice is None:
                    await interaction.response.send_message(
                        f"It's currently {self.target.mention}'s turn to play.",
                        ephemeral=True,
                    )
                    return
                await interaction.response.send_message(
                    (
                        "You've already played your turn."
                        f" ({self.game.player1_choice.emoji})"
                    ),
                    ephemeral=True,
                )
                return

            # Raise an error if it's user's turn and interaction is from target.
            if (
                self.state == _RPSGameState.USER_CHOICE
                and interaction.user.id != self.user.id
            ):
                if self.game.player2_choice is None:
                    await interaction.response.send_message(
                        f"It's currently {self.user.mention}'s turn to play.",
                        ephemeral=True,
                    )
                    return
                await interaction.response.send_message(
                    (
                        "You've already played your turn."
                        f" ({self.game.player2_choice.emoji})"
                    ),
                    ephemeral=True,
                )
                return

            # Target's turn
            if (
                self.state == _RPSGameState.TARGET_CHOICE
                and self.game.player2_choice is not None
            ):
                self.game.player2_plays(rps_option)
                self.state = _RPSGameState.USER_CHOICE

                await interaction.response.send_message(
                    f"You played {self.game.player2_choice.emoji}.",
                    ephemeral=True,
                )

                notification_embed = discord.Embed(
                    color=self.embed_color,
                    title="Rock, Paper, Scissors !",
                    description=(
                        f"{self.target.mention} played their turn.\n\nIt's"
                        " currently {self.user.mention}'s turn to play."
                    ),
                    timestamp=self.timestamp,
                )
                # Send notification embed.
                if self.slash_command:
                    await self.interaction.edit_original_response(
                        content=None,
                        embed=notification_embed,
                    )
                    await self.interaction.followup.send(
                        f"{self.user.mention}, It's your turn now !",
                    )
                else:
                    await self.msg.edit(content=None, embed=notification_embed)
                    await self.msg.reply(f"{self.user.mention}, It's your turn now !")

            # User's turn
            elif (
                self.state == _RPSGameState.USER_CHOICE
                and self.game.player1_choice is not None
            ):
                self.game.player1_plays(rps_option)
                self.state = _RPSGameState.RESULT

                await interaction.response.send_message(
                    f"You played {self.game.player1_choice.emoji}.",
                    ephemeral=True,
                )

                await self.finish_game()

        return callback

    async def finish_game(self) -> None:
        """Finish and calculate the result of the game."""
        if (
            self.game.player1_choice is not None
            and self.game.player2_choice is not None
        ):
            # Calculate the RPS winner.
            winner_user_id = self.game.calculate_winner()
            # Draw
            if winner_user_id is None:
                description = "**It was a Draw !**"
                bot_dialogue = (
                    f"{self.user.mention} escaped this time."
                    if self.bot_plays
                    else None
                )
                winner_thumbnail = None

            # User wins.
            elif winner_user_id == self.user.id:
                description = f"**{self.user.mention} has Won !**"
                bot_dialogue = "-ahh. maybe another time." if self.bot_plays else None
                winner_thumbnail = self.user.display_avatar.url

            # Target wins.
            else:
                description = (
                    f"**{self.target.mention} has Won !**"
                    if not self.bot_plays
                    else "**I have Won !**"
                )
                bot_dialogue = (
                    "huh. not even a single sweat-" if self.bot_plays else None
                )
                winner_thumbnail = self.target.display_avatar.url

            result_embed = (
                discord.Embed(
                    color=self.embed_color,
                    title="Rock, Paper, Scissors ! ",
                    description=description,
                    timestamp=self.timestamp,
                )
                .set_footer(text=bot_dialogue)
                .add_field(
                    name=f"{self.user.display_name} Choice",
                    value=(
                        f"{self.game.player1_choice.name}"
                        f" {self.game.player1_choice.emoji}"
                    ),
                    inline=True,
                )
                .add_field(
                    name=f"{self.target.display_name} Choice",
                    value=(
                        f"{self.game.player2_choice.name}"
                        f" {self.game.player2_choice.emoji}"
                    ),
                    inline=True,
                )
                .set_thumbnail(url=winner_thumbnail)
            )
            # Send result embed.
            if self.slash_command:
                await self.interaction.edit_original_response(
                    embed=result_embed,
                    view=None,
                )
            else:
                await self.msg.edit(embed=result_embed, view=None)

            # Stop the view.
            self.stop()

    async def on_timeout(self) -> None:
        # Disable all buttons upon timeout.
        for btn in self.children:
            if isinstance(btn, discord.ui.Button):
                btn.disabled = True

        if self.bot_plays:
            description = f"{self.user.mention} didn't make a move.\n*shame on you..*"
        elif self.state == _RPSGameState.TARGET_CHOICE:
            description = (
                f"{self.target.mention} didn't seem brave enough"
                " to accept the challenge."
            )
        else:
            description = (
                f"{self.user.mention} seemed to have more important buisness to do."
            )

        timeout_embed = discord.Embed(
            color=discord.Color.dark_gray(),
            title="Rock, Paper, Scissors !",
            description=f"⏰ The game has timed out! {description}",
            timestamp=self.timestamp,
        )
        # Send timeout embed.
        try:
            if self.slash_command:
                await self.interaction.edit_original_response(
                    content=None,
                    embed=timeout_embed,
                    view=self,
                )
            else:
                await self.msg.edit(content=None, embed=timeout_embed, view=self)
        except discord.NotFound:
            pass

        # Stop the view.
        self.stop()

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ) -> None:
        logger.error(
            "❌ Something went wrong with rps interaction - button: %s",
            getattr(item, "label", "unknown"),
            exc_info=error,
        )
        try:
            await interaction.response.send_message(
                "Something went wrong with **rps**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **rps**.",
                ephemeral=True,
            )

        # Stop the view.
        self.stop()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Rps(bot))
