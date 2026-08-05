import asyncio
import random
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from cogs.games.rps import Choice, choices, rpsResult
from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)

people = 40  # number of people to vote in the ballotbox


class Vrps(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Games,
        is_dm_only=False,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=(
            "A game between two people. yet needed a whole class-"
            "\nFirst, everyone in the class draws either a Rock, Paper or Scissors on a card. Then they drop those cards into the ballot box so players can't see them."
            "\nPlayers both draw *three* cards from the box, choose just one, and play *Rock, Paper, Scissors !*."
            "\nIf it's a stalemate, both players draw from the remaining two cards and play again. If it's a stalemate all three times, it's a draw."
            "\nThat makes up one game."
            "\nUnlike normal Rock-Paper-Scissors, players don't always show their entire hand. Trying to read each other under such unfair circumstances is the appeal."
            "\nYou can only play with Amélie herself if you run this game in her dm."
        ),
        brief="Classic rock-paper-scissors, but played with predetermined drawings on cards.",
        usage="<target[*optional*]>",
        aliases=["voterps", "voterockpaperscissors"],
    )

    @commands.command(name="vrps", **Help.to_kwargs)
    async def vrps(
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

        view = ReadyView(ctx, target) if target else VrpsView(ctx, ctx.me, botPlay=True)
        await view.start()

    @vrps.error
    async def vrps_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ):
        logger.exception(f"❌ something went wrong with vrps command:")
        await ctx.reply("something went wrong with **vrps**.")

    # vrps slash command
    @app_commands.command(name="vrps", description=Help.brief, extras=Help.extras)
    @app_commands.describe(user="The user you want to play vrps with.")
    async def slashVrps(
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
            view = ReadyView(interaction, target)
            await view.start()
        else:
            if isinstance(interaction.client.user, discord.abc.User):
                view = VrpsView(interaction, interaction.client.user, botPlay=True)
                await view.start()

    @slashVrps.error
    async def slashVrps_error(self, interaction: discord.Interaction, error: Exception):
        logger.exception(f"❌ something went wrong with /vrps command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **vrps**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **vrps**.", ephemeral=True
            )


class ReadyView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        target: discord.abc.User,
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
        self.embedColor = discord.Color.random()
        self.timestamp = discord.utils.utcnow()

    async def start(self):
        content = f"{self.target.mention}, You're challenged to a game of *Vote Rock, Paper, Scissors !* by {self.user.mention}."
        readyEmbed = discord.Embed(
            title="Vote Rock, Paper, Scissors !",
            description=f"{self.target.mention}, Click `Ready` to start the game.",
            color=self.embedColor,
            timestamp=self.timestamp,
        )
        if self.slash:
            await self.interaction.response.send_message(
                content=content, embed=readyEmbed, view=self
            )
        else:
            self.msg = await self.ctx.reply(
                content=content, embed=readyEmbed, view=self
            )  # saves the message to edit later

    # defining ready button
    @discord.ui.button(label="Ready", emoji="✅", style=discord.ButtonStyle.green)
    async def ready(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ):
        # checks if only the user and target can interact with buttons
        if interaction.user.id not in (self.user.id, self.target.id):
            return await interaction.response.send_message(
                "This isn't your game.", ephemeral=True
            )

        # if user trys to hit ready
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message(
                f"{self.target.mention} must get ready to start the game.",
                ephemeral=True,
            )

        # initializing the vrps view
        view = VrpsView(
            ctx=self.interaction if self.slash else self.ctx,
            target=self.target,
            msg=(
                self.msg if not self.slash else None
            ),  # stores the message in vrps view to edit later
            embedColor=self.embedColor,
            timestamp=self.timestamp,
        )

        await interaction.response.send_message(
            f"{self.user.mention}, {self.target.display_name} has accepted your challenge !"
        )  # notifies the user that target has accepted the challenge

        self.stop()
        await view.start()  # starts the vrps view

    async def on_timeout(self):
        self.ready.disabled = True  # disables ready button

        timeoutEmbed = discord.Embed(
            title="Vote Rock, Paper, Scissors !",
            description=f"⏰ The game has timed out! {self.target.mention} didn't get ready.\n*shame on you..*",
            color=discord.Color.dark_gray(),
            timestamp=self.timestamp,
        )
        try:
            # sends the timeout message
            if self.slash:
                await self.interaction.edit_original_response(
                    content=None, embed=timeoutEmbed, view=self
                )
            else:
                await self.msg.edit(content=None, embed=timeoutEmbed, view=self)

        # if message is already deleted
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
            f"❌ something went wrong with vrps ready interaction - button: {getattr(item, 'label', 'unknown')}"
        )
        try:
            await interaction.response.send_message(
                "something went wrong with **vrps**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **vrps**.", ephemeral=True
            )
        except Exception:
            pass

        self.stop()  # stops the view upon error


# specifies each deck info type
class ChoiceStatus:
    def __init__(self, choice: Choice):
        self.card = choice
        self.shown = False
        self.match = 0


class Deck:
    def __init__(self, ballotbox: list[Choice]):
        self.cards = [ChoiceStatus(ballotbox.pop()) for _ in range(3)]

    def DeckStr(self, final: bool):
        s = f"{'\u00a0' * 8}".join(
            (
                "🎴"
                if not card.shown
                else f"{card.card.emoji} ({card.match}{'st' if card.match == 1 else 'nd' if card.match == 2 else 'rd'})"
            )
            for card in self.cards
        )
        f = f"{'\u00a0' * 8}".join(
            (
                f"{card.card.emoji} ({card.match}{'st' if card.match == 1 else 'nd' if card.match == 2 else 'rd'})"
                if card.match != 0
                else f"{card.card.emoji}"
            )
            for card in self.cards
        )
        return s if not final else f


class VrpsView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        target: discord.abc.User,
        botPlay: bool = False,
        msg: discord.Message | None = None,
        embedColor: discord.Color | None = None,
        timestamp: datetime | None = None,
    ):
        super().__init__(timeout=180)
        if isinstance(ctx, discord.Interaction):
            self.slash = True
            self.interaction = ctx
        else:
            self.slash = False
            self.ctx = ctx
            self.msg = msg
        self.user = self.interaction.user if self.slash else self.ctx.author
        self.target = target
        self.botPlay = botPlay
        self.embedColor = embedColor or discord.Color.random()
        self.timestamp = timestamp or discord.utils.utcnow()
        self.userChoice: Choice | None = None
        self.targetChoice: Choice | None = None
        self.ballotbox: list[Choice] = [
            random.choice(choices) for _ in range(people)
        ]  # creates the ballot box
        random.shuffle(self.ballotbox)  # shuffles the ballotbox

        # distributing cards
        self.userDeck = Deck(self.ballotbox)
        self.targetDeck = Deck(self.ballotbox)

        # defining card buttons
        for i in range(3):
            button: discord.ui.Button[discord.ui.View] = discord.ui.Button(
                emoji="🎴", style=discord.ButtonStyle.gray, row=0
            )
            button.callback = self.make_callback(deckIndex=i)
            self.add_item(button)

    def playersDeckStr(self, final: bool = False):
        return f"{self.targetDeck.DeckStr(final)}{'\u00a0' * 8}<- {self.target.display_name}\n\n{self.userDeck.DeckStr(final)}{'\u00a0' * 8}<- {self.user.display_name}"

    async def start(self):
        votingPhaseEmbed = discord.Embed(
            title="Vote Rock, Paper, Scissors !",
            description=f"Voting Phase begins now!\n**{people}** people are voting for cards..",
            color=self.embedColor,
            timestamp=self.timestamp,
        )
        if self.slash:
            if self.interaction.response.is_done():
                await self.interaction.edit_original_response(
                    content=None, embed=votingPhaseEmbed, view=None
                )
            else:
                await self.interaction.response.send_message(
                    content=None, embed=votingPhaseEmbed
                )
        else:
            if self.msg:
                await self.msg.edit(content=None, embed=votingPhaseEmbed, view=None)
            else:
                await self.ctx.reply(content=None, embed=votingPhaseEmbed)

        await asyncio.sleep(3)  # adds a short delay

        if self.botPlay:
            desc = (
                "Everyone has dropped their votes in the ballot box."
                "\n**Three** cards have been drawn from the Box for each of us."
                "\n\n*And now.. It's SHOWTIME!!* let's do it- *Rock, Paper, Scissors !*"
            )
        else:
            desc = (
                "Everyone has dropped their votes in the ballot box."
                "\n**Three** cards have been drawn from the Box for each of you."
                "\n\n*And now.. It's SHOWTIME!!* choose one card and play *Rock, Paper, Scissors !*"
            )

        matchEmbed = discord.Embed(
            title="Vote Rock, Paper, Scissors !",
            description=desc + f"\n\n{self.playersDeckStr()}",
            color=self.embedColor,
            timestamp=self.timestamp,
        )
        if self.slash:
            await self.interaction.edit_original_response(embed=matchEmbed, view=self)
        else:
            if self.msg:
                await self.msg.edit(embed=matchEmbed, view=self)

    # defining info button
    @discord.ui.button(label="show my deck", style=discord.ButtonStyle.grey, row=1)
    async def deck(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ):
        # checks if only the user and target can interact with the buttons
        if interaction.user.id not in (self.user.id, self.target.id):
            return await interaction.response.send_message(
                "This isn't your game.", ephemeral=True
            )

        # shows users deck info
        if interaction.user.id == self.user.id:
            info = " | ".join(
                (
                    f"{i}.🎴 -> {card.card.emoji}"
                    if not card.shown
                    else f"{i}.🎴 -> (Shown)"
                )
                for i, card in enumerate(self.userDeck.cards, start=1)
            )
            await interaction.response.send_message(info, ephemeral=True)

        # shows targets deck info
        if interaction.user.id == self.target.id:
            info = " | ".join(
                (
                    f"{i}.🎴 -> {card.card.emoji}"
                    if not card.shown
                    else f"{i}.🎴 -> (Shown)"
                )
                for i, card in enumerate(self.targetDeck.cards, start=1)
            )
            await interaction.response.send_message(info, ephemeral=True)

    def make_callback(self, deckIndex: int):
        async def callback(interaction: discord.Interaction):
            # checks if only the user and target can interact with the buttons
            if interaction.user.id not in (self.user.id, self.target.id):
                return await interaction.response.send_message(
                    "This isn't your game.", ephemeral=True
                )

            # the bot makes a random card from its deck to show if playing with bot in the current match
            if self.botPlay and not self.targetChoice:
                botChoiceList = [
                    i for i, card in enumerate(self.targetDeck.cards) if not card.shown
                ]
                botChoice = random.choice(botChoiceList)
                self.targetChoice = self.targetDeck.cards[botChoice].card
                self.targetDeck.cards[botChoice].match = 4 - len(
                    botChoiceList
                )  # stores the nth pick
                self.targetDeck.cards[
                    botChoice
                ].shown = True  # stores the chosen card from the bots deck

            # user chooses a card to show
            if interaction.user.id == self.user.id:
                if not self.userChoice:
                    if self.userDeck.cards[deckIndex].shown:
                        return await interaction.response.send_message(
                            "You have already played this card before. Choose another card.",
                            ephemeral=True,
                        )
                    self.userChoice = self.userDeck.cards[deckIndex].card
                    self.userDeck.cards[deckIndex].match = 4 - sum(
                        1 for card in self.userDeck.cards if not card.shown
                    )  # stores the nth pick
                    self.userDeck.cards[
                        deckIndex
                    ].shown = True  # stores the chosen card from the users deck for the next match
                    await interaction.response.send_message(
                        f"You have shown {self.userChoice.emoji}.",
                        ephemeral=True,
                    )

                # if the user has already shown his card in the current match
                else:
                    return await interaction.response.send_message(
                        f"You have already played your turn in this match. ({self.userChoice.emoji})",
                        ephemeral=True,
                    )

            # target chooses a card if not playing wth bot
            if interaction.user.id == self.target.id:
                if not self.targetChoice:
                    if self.targetDeck.cards[deckIndex].shown:
                        return await interaction.response.send_message(
                            "You have already played this card before. Choose another card.",
                            ephemeral=True,
                        )

                    self.targetChoice = self.targetDeck.cards[deckIndex].card
                    self.targetDeck.cards[deckIndex].match = 4 - sum(
                        1 for card in self.targetDeck.cards if not card.shown
                    )  # stores the nth pick
                    self.targetDeck.cards[
                        deckIndex
                    ].shown = True  # stores the chosen card from the targets deck for the next match
                    await interaction.response.send_message(
                        f"You have shown {self.targetChoice.emoji}",
                        ephemeral=True,
                    )

                # if the target has already shown his card in the current match
                else:
                    return await interaction.response.send_message(
                        f"You have already played your turn in this match. ({self.targetChoice.emoji})",
                        ephemeral=True,
                    )

            # if both players play their card in the current match
            if self.targetChoice and self.userChoice:
                winner = rpsResult(
                    (self.target, self.targetChoice),
                    (self.user, self.userChoice),
                )  # getting the result of rps in the current match

                if winner:
                    if winner.id == self.target.id:
                        desc = (
                            f"**{self.target.mention} has Won!**"
                            if not self.botPlay
                            else "**I have Won!**"
                        )
                    else:
                        desc = f"**{self.user.mention} has Won!**"

                    resultEmbed = discord.Embed(
                        title="Vote Rock, Paper, Scissors !",
                        description=desc + f"\n\n{self.playersDeckStr(final=True)}",
                        color=self.embedColor,
                        timestamp=self.timestamp,
                    ).set_thumbnail(url=winner.display_avatar.url)
                    if self.slash:
                        await self.interaction.edit_original_response(
                            embed=resultEmbed, view=None
                        )
                    else:
                        if self.msg:
                            await self.msg.edit(embed=resultEmbed, view=None)

                    self.stop()

                # draw
                else:
                    # if no card is left in players' deck to play with (match 3)
                    if all(card.shown for card in self.userDeck.cards):
                        resultEmbed = discord.Embed(
                            title="Vote Rock, Paper, Scissors !",
                            description="All Three matches ended in a Draw. This game is a Draw.\n\n*What are the odds??*"
                            + f"\n\n{self.playersDeckStr(final=True)}",
                            color=discord.Color.default(),
                            timestamp=self.timestamp,
                        )
                        if self.slash:
                            await self.interaction.edit_original_response(
                                embed=resultEmbed, view=None
                            )
                        else:
                            if self.msg:
                                await self.msg.edit(embed=resultEmbed, view=None)

                        self.stop()

                    # players still have unplayed cards in their deck, a new match begins
                    else:
                        self.targetChoice = self.userChoice = (
                            None  # resets players' choice for a new match
                        )

                        desc = f"It was a Draw ! The game will continue with the remaining cards in {'your' if not self.botPlay else 'our'} deck.\n\n"
                        nextMatchEmbed = discord.Embed(
                            title="Vote Rock, Paper, Scissors !",
                            description=desc + self.playersDeckStr(),
                            color=self.embedColor,
                            timestamp=self.timestamp,
                        )
                        if self.slash:
                            await self.interaction.edit_original_response(
                                embed=nextMatchEmbed
                            )
                        else:
                            if self.msg:
                                await self.msg.edit(embed=nextMatchEmbed)

        return callback

    async def on_timeout(self):
        # disables all the buttons upon timeout
        for btn in self.children:
            if isinstance(btn, discord.ui.Button):
                btn.disabled = True

        if not self.botPlay and not self.targetChoice and not self.userChoice:
            guilty = "both players"
        elif self.userChoice:
            guilty = self.target.mention
        else:
            guilty = self.target.mention

        timeoutEmbed = discord.Embed(
            title="Vote Rock, Paper, Scissors !",
            description=f"⏰ The game has timed out! {guilty} didn't make a move.\n*shame on you..*",
            color=discord.Color.dark_gray(),
            timestamp=self.timestamp,
        )
        try:
            if self.slash:
                await self.interaction.edit_original_response(
                    content=None, embed=timeoutEmbed, view=self
                )
            else:
                if self.msg:
                    await self.msg.edit(content=None, embed=timeoutEmbed, view=self)

        # if message is already deleted
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
            f"❌ something went wrong with vrps interaction - button: {getattr(item, 'label', 'unknown')}"
        )
        try:
            await interaction.response.send_message(
                "something went wrong with **vrps**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **vrps**.", ephemeral=True
            )
        except Exception:
            pass

        self.stop()  # stops the view upon error


async def setup(bot: commands.Bot):
    await bot.add_cog(Vrps(bot))
