"""Send anonymous messages to someone."""

from __future__ import annotations

__all__ = []

from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.anonymous import (
    PUBLIC_ID_LENGTH,
    AnonymousUser,
    Contact,
    get_anonymous_user,
)
from core.database import execute, fetchone
from core.dbconstants import AnonymousContactTable, AnonSessionTable, AnonymousUserTable
from core.help import HelpData
from core.log_handler import setup_logger
from core.session import Session, get_session

logger = setup_logger(__name__)


@final
class AnonSend(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    Help = HelpData(
        category=HelpData.CommandCategory.ANONYMOUSE,
        is_dm_only=True,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=(
            "Starts an Anonymous messaging session."
            "\n\nUser can send as many messages as they want and send them anonymously"
            "\nto the recipient."
            "\n\nRecipient won't know the sender identity but a private anonymous ID"
            "\nspetialized for the sender."
            "\n\nRecipient can reply to this session later if they want to."
            "\n(try `/help anonreply` for more information)"
        ),
        brief="Sends an Anonymous message.",
        usage="<public_id>",
        aliases=["anons"],
    )

    @commands.command(name="anonsend", **Help.kwargs)
    async def anonsend(
        self,
        ctx: commands.Context[commands.Bot],
        public_id: str | None,
    ) -> None:
        # Warn user if trying to run the command in guild.
        if ctx.guild is not None:
            await ctx.reply("This command can only be used in Amélie's dm.")
            return

        # Warn user if they have an active messaging session.
        if get_session(ctx.author.id, Session.SessionTypes.MESSAGING) is not None:
            await ctx.reply(
                "You have an open messaging session, close it first and try again.",
            )
            return

        # Warn user if no public ID is given.
        if public_id is None:
            await ctx.reply(
                "You must enter user's public ID to send anonymous message to them.",
            )
            return

        # Warn user if given public ID length is not valid.
        if len(public_id) != PUBLIC_ID_LENGTH:
            await ctx.reply("Enter a valid public ID.")
            return

        # Fetch anonymous reciever.
        anon_reciever = await get_anonymous_user(public_id=public_id)

        # Warn user if reciever anonymous account doesn't exist.
        if anon_reciever is None:
            await ctx.reply("User with this ID doesn't exist.")
            return

        # Fetch reciever's real account.
        reciever = self.bot.get_user(
            anon_reciever.user_id,
        ) or await self.bot.fetch_user(
            anon_reciever.user_id,
        )

        # Fetch contact's private ID.
        contact = await anon_reciever.get_contact(contact_id=ctx.author.id)

        # Create anonymous contact if it doesn't exist yet.
        if contact is None:
            contact = await anon_reciever.add_contact(ctx.author.id)

        # Warn user if they are blocked.
        if contact["blocked"]:
            await ctx.reply("You can't send anonymous messages to this user.")
            return

        # Open a messaging session.
        session = Session(user_id=ctx.author.id, type_=Session.SessionTypes.MESSAGING)

        # Initialize view.
        await AnonSendView(
            ctx=ctx,
            bot=self.bot,
            session=session,
            reciever_user=reciever,
            reciever_anon_user=anon_reciever,
            contact=contact,
        ).start()

    @anonsend.error
    async def anonsend_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: Exception,
    ) -> None:
        logger.exception("❌ something went wrong with anonsend command:")
        await ctx.reply("something went wrong with **anonsend**.")

    # anonsend slash command
    @app_commands.command(name="anonsend", description=Help.brief, extras=Help.extras)
    @app_commands.describe(
        public_id="The public ID of the person you want to send anonymous message to."
    )
    @app_commands.dm_only()
    async def slashAnonsend(self, interaction: discord.Interaction, public_id: str):
        # if user has an active session
        if (interaction.user.id, Session.SessionTypes.messaging) in Session.sessions:
            return await interaction.response.send_message(
                "You have an open messaging session, close it first and try again.",
                ephemeral=True,
            )

        # if user enters an invalid id
        if len(public_id) != publicIdLength:
            return await interaction.response.send_message(
                "Enter a valid public ID.", ephemeral=True
            )

        # checks if a user with given public id exists
        row = await fetchone(
            f"""
            SELECT {AnonymousUserTable.COL_USER_ID} FROM {AnonymousUserTable.TABLE_NAME}
            WHERE {AnonymousUserTable.COL_PUBLIC_ID} = ?;
            """,
            (public_id,),
        )
        # if user with given public id doesn't exist
        if not row:
            return await interaction.response.send_message(
                "User with this ID doesn't exist.", ephemeral=True
            )

        recieverUser = self.bot.get_user(row["user_id"]) or await self.bot.fetch_user(
            row["user_id"]
        )  # fetches the reciever user

        # fetches the reciever's anon contacts
        row = await fetchone(
            f"""
            SELECT {AnonymousContactTable.COL_ALIAS}, {AnonymousContactTable.COL_IS_BLOCKED} from {AnonymousContactTable.TABLE_NAME}
            WHERE {AnonymousContactTable.COL_RECIPIENT_ID} = ? AND {AnonymousContactTable.COL_USER_ID} = ?;
            """,
            (recieverUser.id, interaction.user.id),
        )
        # if user is not in the target's anon contacts, creates one
        if not row:
            newId = await privateIdGenerator(recieverUser.id)
            await execute(
                f"""
                INSERT INTO {AnonymousContactTable.TABLE_NAME} ({AnonymousContactTable.columns()})
                VALUES (?, ?, ?);
                """,
                (recieverUser.id, interaction.user.id, newId),
            )
            privateId = newId

        # if user contact exists but is blocked
        elif row["blocked"] == 1:
            return await interaction.response.send_message(
                "You can't send anonymous messages to this user.", ephemeral=True
            )

        else:
            privateId: str = row["contact_anon_id"]

        Session(
            userId=interaction.user.id, type_=Session.SessionTypes.messaging
        )  # opens a session

        view = AnonView(
            interaction, recieverUser, public_id, privateId, self.bot
        )  # initializes the Anon View
        await view.start()

    @slashAnonsend.error
    async def slashAnonsend_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        try:
            Session.sessions[
                (interaction.user.id, Session.SessionTypes.messaging)
            ].close()  # ends the session upon error
        except KeyError:
            pass

        logger.exception(f"❌ something went wrong with /Anonsend command:")
        (
            await interaction.response.send_message(
                "something went wrong with **anonsend**.", ephemeral=True
            )
            if not interaction.response.is_done()
            else await interaction.followup.send(
                "something went wrong with **anonsend**.", ephemeral=True
            )
        )


@final
class AnonSendView(discord.ui.View):
    def __init__(
        self,
        *,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        bot: commands.Bot,
        session: Session,
        reciever_user: discord.User,
        reciever_anon_user: AnonymousUser,
        contact: Contact,
    ) -> None:
        super().__init__(timeout=300)
        if isinstance(ctx, discord.Interaction):
            self.slash = True
            self.interaction = ctx
            self.user = ctx.user
        else:
            self.slash = False
            self.ctx = ctx
            self.user = ctx.author
        self.bot = bot
        self.session = session
        self.reciever = reciever_user
        self.anon_user = reciever_anon_user
        self.contact = contact

    async def start(self) -> None:
        initial_embed = discord.Embed(
            title="Anonymous Message",
            description=(
                f"You are texting `{self.reciever.display_name}` anonymously."
                "\nSend as many messages as you want and hit `done` to close"
                "\nthe interaction."
            ),
            color=discord.Color.blurple(),
        )
        # Send the initial embed and store the message ID.
        if self.slash:
            await self.interaction.response.send_message(embed=initial_embed, view=self)
            msg = await self.interaction.original_response()
            self.msgId = msg.id
        else:
            self.msg = await self.ctx.reply(embed=initial_embed, view=self)
            self.msgId = self.msg.id

        # Start collecting messages.
        await self.session.collect_message(self.bot, dm_only=True)

    # Define done button.
    @discord.ui.button(label="done", style=discord.ButtonStyle.green, row=0)
    async def done(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],  # noqa: ARG002
    ) -> None:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You can't control this session.",
                ephemeral=True,
            )
            return

        # End the session.
        self.session.close()

        now = discord.utils.utcnow()

        # Cancel if no message is sent.
        if not self.session.messages:
            cancel_embed = discord.Embed(
                title="Anonymous Message",
                description="You sent no message, session ended.",
                color=discord.Color.dark_gray(),
                timestamp=now,
            )
            await interaction.response.edit_message(embed=cancel_embed, view=None)

            self.stop()
            return

        # creates the session id
        row = await fetchone(
            f"""
            SELECT COALESCE(MAX({AnonSessionTable.COL_SESSION_ID}), 0) + 1
            FROM {AnonSessionTable.TABLE_NAME}
            WHERE {AnonSessionTable.COL_RECEIVER_ID} = ?
            AND {AnonSessionTable.COL_CONTACT_ANON_ID} = ?;
            """,  # noqa: S608
            (self.reciever.id, self.contact),
        )
        sessionId: int = row[0] if row else 1

        # stores the session in the database
        await execute(
            f"""
            INSERT INTO {AnonSessionTable.TABLE_NAME} ({AnonSessionTable.columns()})
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (sessionId, self.reciever.id, self.contact, self.msgId, now),
        )

        await interaction.response.defer()

        # send the messages to the target
        recieverNotifEmbed = discord.Embed(
            title="New Anonymous Message !",
            description=(
                f"User with ID: `{self.contact}` (Session ID: *{sessionId}*) has sent you these messages:"
            ),
            color=discord.Color.blurple(),
            timestamp=now,
        )
        msg = await self.reciever.send(
            embed=recieverNotifEmbed
        )  # sends an initial message to the reciever

        # replies the collected messages
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
            title="Anonymous Message",
            description=f"Your messages have been sent to `{self.reciever.name}` succesfully. (Session ID: *{sessionId}*)",
            color=discord.Color.green(),
            timestamp=now,
        )
        # await interaction.response.edit_message(embed=senderNotifEmbed, view=None)

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

        self.session.close()  # ends the session

        # sends the cancel message to the user
        cancelEmbed = discord.Embed(
            title="Anonymous Message",
            description="You canceled the session.",
            color=discord.Color.dark_gray(),
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=cancelEmbed, view=None)

        self.stop()

    async def on_timeout(self):
        # disables buttons on timeout
        for btn in self.children:
            if isinstance(btn, discord.ui.Button):
                btn.disabled = True

        self.session.close()  # ends the session upon timeout

        # sends the timeout message
        timeoutEmbed = discord.Embed(
            title="Anonymous Message", description=f"⏰ Session timeout."
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

        self.stop()

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ):
        self.session.close()  # ends the session upon error

        logger.exception(
            f"❌ something went wrong with anonsend interaction - button: {getattr(item, 'label', 'unknown')}"
        )
        (
            await interaction.response.send_message(
                "something went wrong with **anonsend**.", ephemeral=True
            )
            if not interaction.response.is_done()
            else await interaction.followup.send(
                "something went wrong with **anonsend**.", ephemeral=True
            )
        )

        self.stop()


async def setup(bot: commands.Bot):
    await bot.add_cog(AnonSend(bot))
