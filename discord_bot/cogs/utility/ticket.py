"""ticket command."""

from __future__ import annotations

__all__ = []

import json
from pathlib import Path
from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.database import execute
from core.dbconstants import TicketTable
from core.help_data_constants import TICKET_HELP
from core.log_handler import setup_logger
from core.session import Session, get_session
from discord_bot.message_collector import MessageCollector

with Path("config.json").open("r") as file:
    CONFIG = json.load(file)
RECEIVER_ADMIN_ID = CONFIG["ADMINS"][0]

logger = setup_logger(__name__)


@final
class Ticket(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="ticket", **TICKET_HELP.kwargs)
    async def ticket(
        self,
        ctx: commands.Context[commands.Bot],
        subject: str | None,
    ) -> None:
        # Raise an error if user wants to open a ticket in a guild.
        if ctx.guild is not None:
            await ctx.reply("This command can only be used in Amélie's dm.")
            return

        session = get_session(ctx.author.id, Session.SessionTypes.MESSAGING)
        # Raise an error if user has an open messaging session.
        if session is not None:
            await ctx.reply(
                "You have an open messaging session, try closing it and try again.",
            )
            return

        # Raise an error if user enters no subject.
        if subject is None:
            await ctx.reply("You must enter a subject to open the Ticket.")
            return

        # Open a messaging session.
        session = Session(ctx.author.id, Session.SessionTypes.MESSAGING)

        # Fetch the admin or the channel the ticket must be sent to.
        admin = (
            self.bot.get_user(RECEIVER_ADMIN_ID)
            or await self.bot.fetch_user(RECEIVER_ADMIN_ID)
            or self.bot.get_channel(RECEIVER_ADMIN_ID)
            or await self.bot.fetch_channel(RECEIVER_ADMIN_ID)
        )

        # Start the view.
        await TicketView(ctx, subject, session, admin).start()

    @ticket.error
    async def ticket_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        session = get_session(ctx.author.id, Session.SessionTypes.MESSAGING)
        if session is not None:
            session.close()

        logger.error("❌ Something went wrong with ticket command:", exc_info=error)
        await ctx.reply("Something went wrong with **ticket**.")

    # ticket slash command
    @app_commands.command(
        name="ticket",
        description=TICKET_HELP.brief,
        extras=TICKET_HELP.extras,
    )
    @app_commands.describe(subject="The subject of the Ticket.")
    @app_commands.dm_only()
    async def slash_ticket(
        self,
        interaction: discord.Interaction,
        subject: str,
    ) -> None:
        session = get_session(interaction.user.id, Session.SessionTypes.MESSAGING)
        # Raise an error if user has an open messaging session.
        if session is not None:
            await interaction.response.send_message(
                "You have an open messaging session, try closing it and try again.",
                ephemeral=True,
            )
            return

        # Open a messaging session.
        session = Session(interaction.user.id, Session.SessionTypes.MESSAGING)

        # Fetch the admin or the channel the ticket must be sent to.
        admin = (
            self.bot.get_user(RECEIVER_ADMIN_ID)
            or await self.bot.fetch_user(RECEIVER_ADMIN_ID)
            or self.bot.get_channel(RECEIVER_ADMIN_ID)
            or await self.bot.fetch_channel(RECEIVER_ADMIN_ID)
        )

        # Start the view.
        await TicketView(interaction, subject, session, admin).start()

    @slash_ticket.error
    async def slash_ticket_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        session = get_session(interaction.user.id, Session.SessionTypes.MESSAGING)
        if session is not None:
            session.close()

        logger.error("❌ Something went wrong with /ticket command:", exc_info=error)
        (
            await interaction.response.send_message(
                "Something went wrong with **ticket**.",
                ephemeral=True,
            )
            if not interaction.response.is_done()
            else await interaction.followup.send(
                "Something went wrong with **ticket**.",
                ephemeral=True,
            )
        )


class TicketView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        subject: str,
        session: Session,
        admin: discord.User,
    ) -> None:
        super().__init__(timeout=300)
        if isinstance(ctx, discord.Interaction):
            self.slash_command = True
            self.interaction = ctx
            self.user = self.interaction.user
        else:
            self.slash_command = False
            self.ctx = ctx
            self.user = self.ctx.author
        self.subject: str = subject
        self.session: Session = session
        self.admin: discord.User = admin

    async def start(self) -> None:
        """Start the view."""
        initial_embed = discord.Embed(
            color=discord.Color.blurple(),
            title="Ticket 🎫",
            description=(
                "You have opened a **Ticketing** Session."
                "\nSend as many messages as you want and hit `done` to close the"
                " interaction."
                "\n\n**note: Your *username* and *ID* will be included in the Ticket"
                " for more contact.**"
            ),
            timestamp=discord.utils.utcnow(),
        )
        # Send initial embed.
        if self.slash_command:
            await self.interaction.response.send_message(
                embed=initial_embed,
                view=self,
            )
            self.msg = await self.interaction.original_response()
        else:
            self.msg = await self.ctx.reply(embed=initial_embed, view=self)

        self.message_collector = MessageCollector(self.user.id)
        # Start collecting messages for user.
        await self.message_collector.collect_message(dm_only=True)

    # Done button
    @discord.ui.button(label="Done", style=discord.ButtonStyle.green, row=0)
    async def done(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button[discord.ui.View],
    ) -> None:
        # Raise an error if interaction is not from the user.
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You can't control this session.",
                ephemeral=True,
            )
            return

        now = discord.utils.utcnow()

        # Close the session.
        self.session.close()

        messages: list[discord.Message] = self.message_collector.messages

        # Cancel ticketing if user sends no messages.
        if not messages:
            cancel_embed = discord.Embed(
                color=discord.Color.dark_gray(),
                title="Ticket 🎫",
                description="You sent no message, session ended.",
                timestamp=now,
            )
            await interaction.response.edit_message(embed=cancel_embed, view=None)

            # Stop the view.
            self.stop()

            return

        # Defer the response.
        await interaction.response.defer()

        # Save the ticket in database.
        cursor = await execute(
            f"""
            INSERT INTO {TicketTable.TABLE_NAME} ({TicketTable.columns()})
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,  # noqa: S608
            (None, self.user.id, self.msg.id, self.subject, None, now, None),
        )
        ticket_id = cursor.lastrowid

        admin_notification_embed = discord.Embed(
            color=discord.Color.blurple(),
            title="New Ticket ! 🎫",
            description=(
                f"{self.user.mention} with ID {self.user.id} has sent a Ticket."
            ),
            timestamp=now,
        ).set_footer(text=f"Ticket ID {ticket_id}")
        # Send ticket initial embed to the admin.
        msg = await self.admin.send(
            embed=admin_notification_embed,
        )

        # Reply messages to the initial message.
        for message in self.session.messages:
            if message.stickers:
                for sticker in message.stickers:
                    await msg.reply(sticker.url)
                continue

            content = message.content
            files = [await attachment.to_file() for attachment in message.attachments]
            await msg.reply(content=content, files=files, embeds=message.embeds)

        # sends the succeed message to the user
        notification_embed = discord.Embed(
            color=discord.Color.green(),
            title="Ticket 🎫",
            description="Your Ticket has been sent succesfully.",
            timestamp=now,
        )
        # Send succession notification embed.
        await interaction.edit_original_response(embed=notification_embed, view=None)

        # Stop the view.
        self.stop()

    # cancel button
    @discord.ui.button(label="cancel", style=discord.ButtonStyle.gray, row=0)
    async def cancel(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button[discord.ui.View],
    ) -> None:
        # Raise an error if interaction is not from the user.
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You can't control this session.",
                ephemeral=True,
            )
            return

        now = discord.utils.utcnow()

        # Close the session.
        self.session.close()

        cancel_embed = discord.Embed(
            color=discord.Color.dark_gray(),
            title="Ticket 🎫",
            description="You canceled the session.",
            timestamp=now,
        )
        # Send cancel embed.
        await interaction.response.edit_message(embed=cancel_embed, view=None)

        # Stop the view.
        self.stop()

    async def on_timeout(self) -> None:
        # Disable all buttons upon timeout.
        for btn in self.children:
            if isinstance(btn, discord.ui.Button):
                btn.disabled = True

        # Close the session.
        self.session.close()

        timeout_embed = discord.Embed(
            color=discord.Color.dark_gray(),
            title="Ticket 🎫",
            description="⏰ Ticket session timeout.",
            timestamp=discord.utils.utcnow(),
        )
        # Send timeout embed.
        try:
            if self.slash_command:
                await self.interaction.edit_original_response(
                    embed=timeout_embed,
                    view=self,
                )
            else:
                await self.msg.edit(embed=timeout_embed, view=self)
        except discord.NotFound:
            pass

        self.stop()  # stops the interaction upon timeout

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ) -> None:
        # Close the session.
        self.session.close()

        logger.error(
            "❌ Something went wrong with ticket interaction - button: %s",
            getattr(item, "label", "unknown"),
            exc_info=error,
        )
        (
            await interaction.response.send_message(
                "Something went wrong with **ticket**.",
                ephemeral=True,
            )
            if not interaction.response.is_done()
            else await interaction.followup.send(
                "Something went wrong with **ticket**.",
                ephemeral=True,
            )
        )

        # Stop the view.
        self.stop()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ticket(bot))
