import json

import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.database import Session, execute
from core.dbconstants import TicketTable
from core.log_handler import setup_logger

logger = setup_logger(__name__)

with open("config.json") as file:
    config = json.load(file)
TicketPlaceId = config["ADMINS"][
    0
]  # where tickets should be sent, either admins' dm or a channel


class Ticket(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Utility,
        is_dm_only=True,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=(
            "Opens a ticketing session to contact the staff."
            "\n\nPlease try to include a short subject, a clear description of the issue,"
            " when it happened, and any relevant screenshots or files."
            "\nYou may send multiple messages during the session."
            " Press **done** when finished to submit the ticket."
            "\n\nYour username and user ID will be included automatically for follow-up."
        ),
        brief="Opens a support ticket.",
        usage="<subject>",
        aliases=None,
    )

    @commands.command(name="ticket", **Help.to_kwargs)
    async def ticket(self, ctx: commands.Context[commands.Bot], subject: str | None):
        # if user runs the command in a server
        if ctx.guild:
            return await ctx.reply("This command can only be used in Amélie's dm.")

        # if user already has an active session
        if (ctx.author.id, Session.Types.messaging) in Session.sessions:
            return await ctx.reply(
                "You have an open messaging session, try closing it and try again."
            )

        # if user doesn't enter the ticket subject
        if not subject:
            return await ctx.reply("You must enter a subject to open the Ticket.")

        Session(userId=ctx.author.id, type=Session.Types.messaging)  # starts a session

        admin = (
            self.bot.get_user(TicketPlaceId)
            or await self.bot.fetch_user(TicketPlaceId)
            or self.bot.get_channel(TicketPlaceId)
            or await self.bot.fetch_channel(TicketPlaceId)
        )  # fetches the admin user or channel to send the message to

        view = TicketView(ctx, subject, admin, self.bot)  # initializes the Ticket View
        await view.start()  # starts the view

    @ticket.error
    async def ticket_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ):
        try:
            Session.sessions[
                (ctx.author.id, Session.Types.messaging)
            ].close()  # ends the session upon error
        except KeyError:
            pass

        logger.exception(f"❌ something went wrong with ticket command:")
        await ctx.reply("something went wrong with **ticket**.")

    # ticket slash command
    @app_commands.command(name="ticket", description=Help.brief, extras=Help.extras)
    @app_commands.describe(subject="The subject of the Ticket.")
    @app_commands.dm_only()
    async def slashTicket(self, interaction: discord.Interaction, subject: str):
        # if user already has an active session
        if (interaction.user.id, Session.Types.messaging) in Session.sessions:
            return await interaction.response.send_message(
                "You have an open messaging session, try closing it and try again.",
                ephemeral=True,
            )

        Session(
            userId=interaction.user.id, type=Session.Types.messaging
        )  # starts a session

        admin = (
            self.bot.get_user(TicketPlaceId)
            or await self.bot.fetch_user(TicketPlaceId)
            or self.bot.get_channel(TicketPlaceId)
            or await self.bot.fetch_channel(TicketPlaceId)
        )  # fetches the admin user or channel to send the message to

        view = TicketView(
            interaction, subject, admin, self.bot
        )  # initializes the Ticket View
        await view.start()  # starts the view

    @slashTicket.error
    async def slashTicket_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        try:
            Session.sessions[
                (interaction.user.id, Session.Types.messaging)
            ].close()  # ends the session upon error
        except KeyError:
            pass

        logger.exception(f"❌ something went wrong with /ticket command:")
        (
            await interaction.response.send_message(
                "something went wrong with **ticket**.", ephemeral=True
            )
            if not interaction.response.is_done()
            else await interaction.followup.send(
                "something went wrong with **ticket**.", ephemeral=True
            )
        )


class TicketView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        subject: str,
        admin: discord.User,
        bot: commands.Bot,
    ):
        super().__init__(timeout=300)
        if isinstance(ctx, discord.Interaction):
            self.slash = True
            self.interaction = ctx
            self.user = ctx.user
        else:
            self.slash = False
            self.ctx = ctx
            self.user = ctx.author
        self.subject = subject
        self.admin = admin
        self.bot = bot
        self.session = Session.sessions[(self.user.id, Session.Types.messaging)]

    async def start(self):
        initialEmbed = discord.Embed(
            title="Ticket 🎫",
            description=(
                f"You have opened a **Ticketing** Session."
                "\nSend as many messages as you want and hit `done` to close the interaction."
                "\n\n**note: Your *username* and *ID* will be included in the Ticket for more contact.**"
            ),
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        if self.slash:
            await self.interaction.response.send_message(embed=initialEmbed, view=self)
            msg = await self.interaction.original_response()
            self.collectorId = msg.id  # stores the collector message id
        else:
            self.msg = await self.ctx.reply(embed=initialEmbed, view=self)
            self.collectorId = self.msg.id  # stores the collector message id

        await self.session.collectMessage(
            self.bot, dmOnly=True
        )  # starts collecting messages

    # done button
    @discord.ui.button(label="done", style=discord.ButtonStyle.green, row=0)
    async def done(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "You can't control this session.", ephemeral=True
            )

        timestamp = discord.utils.utcnow()

        self.session.close()  # ends the session

        # if no message is sent, session gets canceled
        if not self.session.messages:
            endEmbed = discord.Embed(
                title="Ticket 🎫",
                description="You sent no message, session ended.",
                color=discord.Color.dark_gray(),
                timestamp=timestamp,
            )
            await interaction.response.edit_message(embed=endEmbed, view=None)

            self.stop()
            return

        # creates a ticket in the database for later response
        cursor = await execute(
            f"""
            INSERT INTO {TicketTable.TABLE_NAME} ({TicketTable.columns()})
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (self.user.id, self.collectorId, self.subject, timestamp),
        )
        ticketId = cursor.lastrowid  # fetches the created ticket id

        await interaction.response.defer()

        # sends the ticket
        adminNotifEmbed = discord.Embed(
            title="New Ticket ! 🎫",
            description=(
                f"{self.user.mention} with ID {self.user.id} has sent a Ticket."
            ),
            color=discord.Color.blurple(),
            timestamp=timestamp,
        ).set_footer(text=f"Ticket ID {ticketId}")
        msg = await self.admin.send(
            embed=adminNotifEmbed
        )  # sends an initial message to the reciever

        # replys the collected messages to the initial message
        for m in self.session.messages:
            # if message is sticker
            if m.stickers:
                for s in m.stickers:
                    await msg.reply(s.url)
                break

            # if message is text, file or embed or combinations of them
            content = m.content
            files = [await a.to_file() for a in m.attachments]

            await msg.reply(content=content, files=files, embeds=m.embeds)

        # sends the succeed message to the user
        senderNotifEmbed = discord.Embed(
            title="Ticket 🎫",
            description=f"Your Ticket has been sent succesfully.",
            color=discord.Color.green(),
            timestamp=timestamp,
        )
        await interaction.edit_original_response(embed=senderNotifEmbed, view=None)

        self.stop()

    # cancel button
    @discord.ui.button(label="cancel", style=discord.ButtonStyle.gray, row=0)
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "You can't control this session.", ephemeral=True
            )

        timestamp = discord.utils.utcnow()

        self.session.close()  # ends the session

        # sends the cancel message to the user
        endEmbed = discord.Embed(
            title="Ticket 🎫",
            description="You canceled the session.",
            color=discord.Color.dark_gray(),
            timestamp=timestamp,
        )
        await interaction.response.edit_message(embed=endEmbed, view=None)

        self.stop()

    async def on_timeout(self):
        # disables buttons on timeout
        for btn in self.children:
            if isinstance(btn, discord.ui.Button):
                btn.disabled = True

        self.session.close()  # ends the session upon timeout

        # sends the timeout message
        timeoutEmbed = discord.Embed(
            title="Ticket 🎫",
            description=f"⏰ Ticket session timeout.",
            color=discord.Color.dark_gray(),
            timestamp=discord.utils.utcnow(),
        )
        try:
            if self.slash:
                await self.interaction.edit_original_response(
                    embed=timeoutEmbed, view=self
                )
            else:
                await self.msg.edit(embed=timeoutEmbed, view=self)
        except discord.NotFound:
            pass

        self.stop()  # stops the interaction upon timeout

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ):
        self.session.close()  # ends the session upon error

        logger.exception(
            f"❌ something went wrong with ticket interaction - button: {getattr(item, 'label', 'unknown')}"
        )
        (
            await interaction.response.send_message(
                "something went wrong with **ticket**.", ephemeral=True
            )
            if not interaction.response.is_done()
            else await interaction.followup.send(
                "something went wrong with **ticket**.", ephemeral=True
            )
        )

        self.stop()  # stops the interaction upon error


async def setup(bot: commands.Bot):
    await bot.add_cog(Ticket(bot))
