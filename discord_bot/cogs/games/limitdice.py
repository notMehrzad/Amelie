from __future__ import annotations

__all__ = []

import random
from enum import Enum, auto
from typing import TypedDict

import discord
from discord import app_commands
from discord.ext import commands

from core.help_data_constants import LIMITDICE_HELP
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class _State(Enum):
    TARGET_ROLL_TURN = auto()
    USER_ROLL_TURN = auto()


class ScoreBoard(TypedDict):
    user: int
    userRecord: list[int | str]
    userBusted: None | int
    target: int
    targetRecord: list[int | str]
    targetBusted: None | int


class LimitDice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="limitdice", **LIMITDICE_HELP.kwargs)
    async def limitdice(
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.User | str | None = None,
    ) -> None:
        if user is None:
            target: discord.Member | None = None
        else:
            # Raise an error if user is not valid.
            if not isinstance(user, discord.abc.User):
                await ctx.reply("User not found. Please mention a valid user.")
                return

            # Raise an error if entered user is user themselves.
            if user.id == ctx.author.id:
                await ctx.reply("You can't play with yourself.")
                return

            if ctx.guild is None:
                # Raise an error if mentioned user is not the bot in DM.
                if user.id != ctx.me.id:
                    await ctx.reply(
                        "You can only play this game with others in a server."
                        " (except me!)",
                    )
                    return

                target = None

            else:
                # Fetch the target from the guild.
                target = ctx.guild.get_member(user.id)
                # Raise an error if target can not be fetched.
                if target is None:
                    await ctx.reply(f"{user.mention} is not a member of this server.")
                    return

                # Raise an error if target is any other bot.
                if target.bot and target.id != ctx.me.id:
                    await ctx.reply("You can't play with bots. (except me!)")
                    return

        await LimitDiceVeiw(ctx, target).start()

    @limitdice.error
    async def limitdice_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error("❌ Something went wrong with limitdice command:", exc_info=error)
        await ctx.reply("Something went wrong with **limitdice**.")

    # limitdice slash command
    @app_commands.command(
        name="limitdice", description=LIMITDICE_HELP.brief, extras=LIMITDICE_HELP.extras
    )
    @app_commands.describe(user="The user you want to play Limit Dice with.")
    async def slash_limitdice(
        self, interaction: discord.Interaction, user: discord.User | None = None
    ):
        # if user mentions itself
        if user and user.id == interaction.user.id:
            return await interaction.response.send_message(
                "You can't play with yourself.", ephemeral=True
            )

        # if the user runs this command in dm to play with another user
        if (
            not interaction.guild
            and user
            and user.id != interaction.client.application_id
        ):
            return await interaction.response.send_message(
                "You can only play this game with others in a server. (except me!)",
                ephemeral=True,
            )

        if user and interaction.guild:
            target = interaction.guild.get_member(user.id)
            if not target:
                return await interaction.response.send_message(
                    f"{user.mention} is not a member of this server.", ephemeral=True
                )
        else:
            target = None

        # if user wants to play with a bot except this bot
        if target and target.bot and target.id != interaction.client.application_id:
            return await interaction.response.send_message(
                "You can't play with bots. (except me!)", ephemeral=True
            )

        # plays with bot if no target is mentioned or the target is the bot itself
        if not target or target.id == interaction.client.application_id:
            if isinstance(interaction.client.user, discord.abc.User):
                view = LimitDiceVeiw(interaction, interaction.client.user, botPlay=True)
                await view.start()

        else:
            view = LimitDiceVeiw(interaction, target)
            await view.start()

    @slash_limitdice.error
    async def slashLimitdice_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        logger.exception(f"❌ something went wrong with /limitdice command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **limitdice**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **limitdice**.", ephemeral=True
            )


class LimitDiceHand:
    def __init__(self) -> None:
        self.user_score: int = 0
        self.user_record: list[int] = []

    @property
    def is_busted(self) -> bool:
        """Return whether the hand is busted."""
        return 6 in self.user_record


class LimitDiceVeiw(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        target: discord.Member | None,
    ) -> None:
        super().__init__(timeout=180)
        if isinstance(ctx, discord.Interaction):
            self.slash_command = True
            self.interaction = ctx
            self.user = self.interaction.user
        else:
            self.slash_command = False
            self.ctx = ctx
            self.user = self.ctx.author

        if target is not None:
            self.target: discord.Member = target
            self.bot_plays = False

        else:
            self.bot_plays = True

        self.playersScore: ScoreBoard = {
            "user": 0,
            "userRecord": [],
            "userBusted": None,
            "target": 0,
            "targetRecord": [],
            "targetBusted": None,
        }
        self.state: _State = _State.TARGET_ROLL_TURN
        self.match = 1

        self.embedColor = discord.Color.random()
        self.timestamp = discord.utils.utcnow()

    async def start(self) -> None:
        """Start the view."""
        if self.bot_plays:
            content = None
            desc = "*limit dice..\nI love this game. shall we start?*\nI already rolled my die."

            await self.roll_for_bot()

        else:
            # Send target a notification.
            content = f"{self.target.mention}, You're challenged to a game of *Limit Dice* by {self.user.mention}."
            desc = f"It's currently {self.target.mention}'s turn to roll the dice."

        start_embed = discord.Embed(
            color=self.embedColor,
            title="Limit Dice 🎲",
            description=desc,
            timestamp=self.timestamp,
        )
        # Send start embed.
        if self.slash_command:
            await self.interaction.response.send_message(
                content=content,
                embed=start_embed,
                view=self,
            )
        else:
            self.msg = await self.ctx.send(
                content=content,
                embed=start_embed,
                view=self,
            )

    async def roll_for_bot(self) -> None:
        if not self.bot_plays:
            return

        if self.state == _State.TARGET_ROLL_TURN:
            # if not busted yet
            if not self.playersScore["targetBusted"]:
                botDie = random.randint(1, 6)  # rolls a die for the bot
                self.playersScore["targetRecord"].append(
                    botDie
                )  # saves the die for the record

                # if rolls a 6, busted
                if botDie == 6:
                    self.playersScore["target"] = 0
                    self.playersScore["targetBusted"] = len(
                        self.playersScore["targetRecord"]
                    )

                    # if the user is busted too, match ends
                    if self.playersScore["userBusted"]:
                        return await self.endMatch(bothBusted=True)

                # adds the score otherwise
                else:
                    self.playersScore["target"] += 1

            self.state = "user_roll"  # ends bots's roll turn, user's roll turn begins
        elif self.state == "target_last_roll":
            botDie = random.randint(1, 6)  # rolls a die for the bot for the last time
            self.playersScore["targetRecord"].append(
                botDie
            )  # saves the die for the record

            # if rolls a 6, busted
            if botDie == 6:
                self.playersScore["target"] = 0
                self.playersScore["targetBusted"] = len(
                    self.playersScore["targetRecord"]
                )

            # adds the score otherwise
            else:
                self.playersScore["target"] += 1

            await self.endMatch()  # ends the match

    # roll button
    @discord.ui.button(label="roll", style=discord.ButtonStyle.green, row=0)
    async def roll(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ):
        # checks if only the user and target can interact with buttons
        if interaction.user.id not in (self.target.id, self.user.id):
            return await interaction.response.send_message(
                "You can't play in this match.", ephemeral=True
            )

        # if user trys to roll when it's target's turn
        if self.state == "target_roll" and interaction.user.id != self.target.id:
            return await interaction.response.send_message(
                f"It's {self.target.mention}'s turn to roll the die.", ephemeral=True
            )

        # if target trys to roll when it's user's turn
        if self.state == "user_roll" and interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                f"It's {self.user.mention}'s turn to roll the die.", ephemeral=True
            )

        # if user trys to roll when it's target's last roll phase
        if self.state == "target_last_roll" and interaction.user.id != self.target.id:
            return await interaction.response.send_message(
                f"You stopped before and your score is frozen in place.\nIt's currently {self.target.mention}'s turn to roll for the last time.",
                ephemeral=True,
            )

        # if target trys to roll when it's user's last roll phase
        if self.state == "user_last_roll" and interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                f"You stopped before and your score is frozen in place.\nIt's currently {self.user.mention}'s turn to roll for the last time.",
                ephemeral=True,
            )

        # target's turn
        if self.state == "target_roll":
            # if not busted yet
            if not self.playersScore["targetBusted"]:
                targetDie = random.randint(1, 6)  # rolls a die for the target
                self.playersScore["targetRecord"].append(
                    targetDie
                )  # saves the die for the record

                # if rolls a 6, busted
                if targetDie == 6:
                    self.playersScore["target"] = 0
                    self.playersScore["targetBusted"] = len(
                        self.playersScore["targetRecord"]
                    )

                    # if the user is busted too, match ends
                    if self.playersScore["userBusted"]:
                        return await self.endMatch(bothBusted=True)
                    else:
                        rollStatus = f"You rolled a **{targetDie}!**\nYour score is reset to 0 and you gain no more point from now on."

                # adds the score otherwise
                else:
                    self.playersScore["target"] += 1
                    rollStatus = f"You rolled a **{targetDie}**.\nYour current score: {self.playersScore['target']}"
            else:
                rollStatus = "You gain no more points."

            await interaction.response.send_message(
                rollStatus, ephemeral=True
            )  # sends the roll result to the target

            if self.match == 1:
                await interaction.followup.send(
                    f"{self.user.mention}, It's your turn now !"
                )  # notifies the user that the target accepted the game

            userRollEmbed = discord.Embed(
                title="Limit Dice 🎲",
                description=(
                    f"{self.target.mention} has rolled their die."
                    f"\n\nIt's currently {self.user.mention}'s turn to roll."
                ),
                color=self.embedColor,
                timestamp=self.timestamp,
            )
            if self.slash_command:
                await self.interaction.edit_original_response(
                    content=None, embed=userRollEmbed
                )
            else:
                await self.msg.edit(content=None, embed=userRollEmbed)

            self.state = "user_roll"  # ends target's roll turn, user's roll turn begins

        # user's turn
        elif self.state == "user_roll":
            self.roll.disabled = True  # disables roll button

            # if not busted yet
            if not self.playersScore["userBusted"]:
                userDie = random.randint(1, 6)  # rolls a die for the user
                self.playersScore["userRecord"].append(
                    userDie
                )  # saves the die for the record

                # if rolls a 6, busted
                if userDie == 6:
                    self.playersScore["user"] = 0
                    self.playersScore["userBusted"] = len(
                        self.playersScore["userRecord"]
                    )

                    # if the target is busted too, match ends
                    if self.playersScore["targetBusted"]:
                        return await self.endMatch(bothBusted=True)
                    else:
                        rollStatus = f"You rolled a **{userDie}!**\nYour score is reset to 0 and you gain no more point from now on."

                # adds the score otherwise
                else:
                    self.playersScore["user"] += 1
                    rollStatus = f"You rolled a **{userDie}**.\nYour current score: {self.playersScore['target']}"
            else:
                rollStatus = "You gain no more points."

            await interaction.response.send_message(
                rollStatus, ephemeral=True
            )  # sends the roll result to the user

            self.proceed.disabled = self.stopbtn.disabled = (
                False  # enables decision buttons, decision phase begins
            )

            if self.botPlay:
                desc = (
                    "Amazing. The decision phase begins now."
                    "\nWe must now decide either to **Roll** again and bring even more fun to this game, or **Stop** and freeze our score !"
                    "\n\nI made my choice already."
                )
            else:
                desc = (
                    "Now that both sides rolled their die, the decision phase begins."
                    "\nYou must decide either to **Roll** or **Stop**."
                    "\nIf both of you stop, showdown phase begins."
                    f"\n\nIt's currently {self.target.mention}'s turn to decide."
                )
            targetDecideEmbed = discord.Embed(
                title="Limit Dice 🎲",
                description=desc,
                color=self.embedColor,
                timestamp=self.timestamp,
            )
            if self.slash_command:
                await self.interaction.edit_original_response(
                    embed=targetDecideEmbed, view=self
                )
            else:
                await self.msg.edit(embed=targetDecideEmbed, view=self)

            self.state = (
                "target_decide"  # ends user's roll turn, target's decide turn begins
            )

        # target's last roll turn
        elif self.state == "target_last_roll":
            self.roll.disabled = True  # disables roll button

            targetDie = random.randint(
                1, 6
            )  # rolls a die for the target for the last time
            self.playersScore["userRecord"].append(targetDie)  # saves for the record

            # if rolls a 6, busted
            if targetDie == 6:
                self.playersScore["user"] = 0
                self.playersScore["userBusted"] = len(self.playersScore["userRecord"])
                rollStatus = f"You rolled a **{targetDie}!**\nYour score is reset to 0."

            # adds the score otherwise
            else:
                self.playersScore["user"] += 1
                rollStatus = f"You rolled a **{targetDie}**.\nYour current score: {self.playersScore['target']}"

            await interaction.response.send_message(
                rollStatus, ephemeral=True
            )  # notifys the user of the result

            await self.endMatch()

        # user's last roll turn
        elif self.state == "user_last_roll":
            self.roll.disabled = True  # disables roll button

            userDie = random.randint(1, 6)  # rolls a die for the user for the last time
            self.playersScore["userRecord"].append(userDie)  # saves for the record

            # if rolls a 6, busted
            if userDie == 6:
                self.playersScore["user"] = 0
                self.playersScore["userBusted"] = len(self.playersScore["userRecord"])
                rollStatus = f"You rolled a **{userDie}!**\nYour score is reset to 0."

            # adds the score otherwise
            else:
                self.playersScore["user"] += 1
                rollStatus = f"You rolled a **{userDie}**.\nYour current score: {self.playersScore['target']}"

            await interaction.response.send_message(
                rollStatus, ephemeral=True
            )  # notifys the user of the result

            await self.endMatch()

    # defines proceed button
    @discord.ui.button(
        label="proceed", style=discord.ButtonStyle.blurple, row=0, disabled=True
    )
    async def proceed(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ):
        # checks if only the user and target can interact with buttons
        if interaction.user.id not in (self.target.id, self.user.id):
            return await interaction.response.send_message(
                "You can't play in this match.", ephemeral=True
            )

        # if user trys to decide when it's target's turn
        if (
            not self.botPlay
            and self.state == "target_decide"
            and interaction.user.id != self.target.id
        ):
            return await interaction.response.send_message(
                f"It's {self.target.mention}'s turn to decide.", ephemeral=True
            )

        # if target trys to decide when it's user's turn
        if self.state == "user_decide" and interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                f"It's {self.user.mention}'s turn to decide.", ephemeral=True
            )

        # bot's turn, if bot is the target
        if self.state == "target_decide" and self.botPlay:
            pass

            self.state = (
                "user_decide"  # ends bot's decide turn, user's decide turn begins
            )

        # target's turn
        if self.state == "target_decide":
            userDecideEmbed = discord.Embed(
                title="Limit Dice 🎲",
                description=(
                    f"{self.target.mention} will **Proceed**. 🔄️"
                    f"\n\nIt's currently {self.user.mention}'s turn to decide."
                ),
                color=self.embedColor,
                timestamp=self.timestamp,
            )
            await interaction.response.edit_message(embed=userDecideEmbed)

            self.state = (
                "user_decide"  # ends target's decide turn, user's decide turn begins
            )

        # user's turn
        elif self.state == "user_decide":
            self.proceed.disabled = self.stopbtn.disabled = (
                True  # disables decision buttons
            )

            # if target stopped, user last roll phase begins
            if "stop" in self.playersScore["targetRecord"]:
                if not self.playersScore["userBusted"]:
                    self.roll.disabled = False  # enables roll button for the last time

                    userProceedEmbed = discord.Embed(
                        title="Limit Dice 🎲",
                        description=(
                            f"{self.target.mention if not self.botPlay else 'I'} {'Stops' if not self.botPlay else 'Stop'} !🤚"
                            f"\n{self.user.mention} Proceeds !🔄️"
                            f"\n\n{self.user.mention} hasn't rolled a six yet so it's their turn to roll for the last time."
                        ),
                        color=self.embedColor,
                        timestamp=self.timestamp,
                    )
                    await interaction.response.edit_message(
                        embed=userProceedEmbed, view=self
                    )

                # if user is busted, match ends
                else:
                    return await self.endMatch()

                self.state = "user_last_roll"  # ends user's decide turn, user's last roll turn begins

            # if target proceeded, another match begins
            else:
                self.match += 1  # increase the match number

                self.roll.disabled = False  # enables roll button for a new match

                bothProceedEmbed = discord.Embed(
                    title="Limit Dice 🎲",
                    description=(
                        f"{self.target.mention if not self.botPlay else 'I'} {'Proceeds' if not self.botPlay else 'Proceed'} !🔄️"
                        f"\n{self.user.mention} Proceeds !🔄️"
                        f"\nRound {self.match} begins."
                        f"\n\nIt's currently {self.target.mention}'s turn to roll their die."
                        if not self.botPlay
                        else "I've rolled my die already."
                    ),
                    color=self.embedColor,
                    timestamp=self.timestamp,
                )
                await interaction.response.edit_message(
                    embed=bothProceedEmbed, view=self
                )

                self.state = "target_roll"  # ends user's decide turn, another match with target's roll turn begins
                if self.botPlay:
                    await self.roll_for_bot()

    # defines stand button
    @discord.ui.button(
        label="stop", style=discord.ButtonStyle.gray, row=0, disabled=True
    )
    async def stopbtn(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ):
        # checks if only the user and target can interact with buttons
        if interaction.user.id not in (self.target.id, self.user.id):
            return await interaction.response.send_message(
                "You can't play in this match.", ephemeral=True
            )

        # if user trys to decide when it's target's turn
        if (
            not self.botPlay
            and self.state == "target_decide"
            and interaction.user.id != self.target.id
        ):
            return await interaction.response.send_message(
                f"It's {self.target.mention}'s turn to decide.", ephemeral=True
            )

        # if target trys to decide when it's user's turn
        if self.state == "user_decide" and interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                f"It's {self.user.mention}'s turn to decide.", ephemeral=True
            )

        # bot's turn, if bot is the target
        if self.state == "target_decide" and self.botPlay:
            self.playersScore["targetRecord"].append("stop")

            self.state = (
                "user_decide"  # ends bot's decide turn, user's decide turn begins
            )

        # target's turn
        if self.state == "target_decide":
            self.playersScore["targetRecord"].append("stop")

            targetStopEmbed = discord.Embed(
                title="Limit Dice 🎲",
                description=(
                    f"{self.target.mention} Stops !🤚"
                    f"\n\nIt's currently {self.user.mention}'s turn to decide."
                ),
                color=self.embedColor,
                timestamp=self.timestamp,
            )
            await interaction.response.edit_message(embed=targetStopEmbed)

            self.state = (
                "user_decide"  # ends target's decide turn, user's decide turn begins
            )

        # users's turn
        elif self.state == "user_decide":
            self.stopbtn.disabled = self.proceed.disabled = (
                True  # disables decision buttons
            )

            self.playersScore["userRecord"].append("stop")

            # if target stopped, match ends
            if "stop" in self.playersScore["targetRecord"]:
                return await self.endMatch(bothStopped=True)

            # if target proceeded, target last roll phase begins
            else:
                self.roll.disabled = False  # enables roll button for the last time

                if not self.playersScore["targetBusted"]:
                    userStopEmbed = discord.Embed(
                        title="Limit Dice 🎲",
                        description=(
                            f"{self.target.mention if not self.botPlay else 'I'} {'Proceeds' if not self.botPlay else 'Proceed'} !🔄️"
                            f"\n{self.user.mention} Stops !🤚"
                            f"\n\n{self.target.mention} hasn't rolled a six yet so it's their turn to roll for the last time."
                        ),
                        color=self.embedColor,
                        timestamp=self.timestamp,
                    )
                    await interaction.response.edit_message(
                        embed=userStopEmbed, view=self
                    )

                # if target is busted, match ends
                else:
                    return await self.endMatch()

                self.state = "target_last_roll"  # ends user's decide turn, target's last roll turn begins
                if self.botPlay:
                    await self.roll_for_bot()

    async def endMatch(self, bothBusted: bool = False, bothStopped: bool = False):
        # draw
        if self.playersScore["target"] == self.playersScore["user"]:
            winner = None
        # target wins
        elif self.playersScore["target"] > self.playersScore["user"]:
            winner = self.target
        # user wins
        else:
            winner = self.user

        if not winner:
            self.roll.disabled = False  # enables roll button

        if bothBusted:
            bothBustedStr = (
                "Both players rolled 6 !\n\n"
                if not self.botPlay
                else "We both rolled 6 !\n\n"
            )
        else:
            bothBustedStr = ""
        if bothStopped:
            bothStoppedStr = (
                "Both players stopped ! and..\n\n"
                if not self.botPlay
                else "We both stopped ! and..\n\n"
            )
        else:
            bothStoppedStr = ""

        # winner string
        if winner:
            winnerStr = (
                f"**{winner.mention} has WON !!**"
                f"\nWith a result of `{max(self.playersScore['target'], self.playersScore['user'])} > {min(self.playersScore['target'], self.playersScore['user'])}`"
            )

            rematchStr = ""
        else:
            winnerStr = (
                f"It's a DRAW !!"
                f"\nWith a result of `{self.playersScore['target']} = {self.playersScore['user']}`"
            )

            rematchStr = (
                "\n\nAnother match has begun to determine the winner."
                f"\nIt's currently {self.target.mention}'s turn to roll the die."
                if not self.botPlay
                else "\nI rolled my die already."
            )  # rematch string

        # busted string
        if self.playersScore["targetBusted"] and self.playersScore["userBusted"]:
            bustedStr = f"\n\nBoth {self.target.mention if not self.botPlay else 'I'} and {self.user.mention} were busted from match {self.playersScore['targetBusted']} and {self.playersScore['userBusted']} actually."
        elif self.playersScore["targetBusted"]:
            bustedStr = f"\n\n{self.target.mention if not self.botPlay else 'I'} was busted from match {self.playersScore['targetBusted']} actually."
        elif self.playersScore["userBusted"]:
            bustedStr = f"\n\n{self.user.mention} was busted from match {self.playersScore['userBusted']} actually."
        else:
            bustedStr = ""

        resultEmbed = discord.Embed(
            title="Limit Dice 🎲",
            description=bothBustedStr
            + bothStoppedStr
            + winnerStr
            + rematchStr
            + bustedStr,
            color=self.embedColor,
            timestamp=self.timestamp,
        )
        if self.slash_command:
            await self.interaction.edit_original_response(
                embed=resultEmbed, view=self if not winner else None
            )
        else:
            await self.msg.edit(embed=resultEmbed, view=self if not winner else None)

        # if draw, rematch
        if not winner:
            # resets stats for a rematch
            self.playersScore["target"] = self.playersScore["user"] = 0
            self.playersScore["targetRecord"] = self.playersScore["userRecord"] = []
            self.playersScore["targetBusted"] = self.playersScore["userBusted"] = None

            self.state = "target_roll"  # a new match begins with target's roll turn
            if self.botPlay:
                await self.roll_for_bot()
        else:
            self.stop()  # stops the view

    async def on_timeout(self):
        # disables buttons on timeout
        for btn in self.children:
            if isinstance(btn, discord.ui.Button):
                btn.disabled = True

        if self.botPlay:
            if self.state in ("target_roll", "user_roll"):
                guiltyStr = f"{self.user.mention} didn't roll their die. Pathetic."
            else:
                guiltyStr = f"{self.user.mention} couldn't decide a simple decision."
        elif self.state == "target_roll":
            guiltyStr = f"{self.target.mention} didn't roll their die. Pathetic."
        elif self.state == "target_decide":
            guiltyStr = f"{self.target.mention} couldn't decide a simple decision."
        elif self.state == "user_roll":
            guiltyStr = f"{self.user.mention} didn't roll their die. Pathetic."
        else:
            guiltyStr = f"{self.user.mention} couldn't decide a simple decision."

        toEmbed = discord.Embed(
            title="Limit Dice 🎲",
            description=f"⏰ The game has timed out! {guiltyStr}",
            color=discord.Color.dark_gray(),
            timestamp=self.timestamp,
        )
        try:
            # sends the timeout message
            if self.slash_command:
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
            f"❌ something went wrong with limitdice interaction - button: {getattr(item, 'label', 'unknown')}"
        )
        try:
            await interaction.response.send_message(
                "something went wrong with **limitdice**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **limitdice**.", ephemeral=True
            )
        except Exception:
            pass

        self.stop()  # stops the view upon error


async def setup(bot: commands.Bot):
    await bot.add_cog(LimitDice(bot))
