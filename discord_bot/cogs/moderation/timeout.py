import re
from datetime import timedelta, timezone

import dateparser
import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)


def timeDeltaParser(untilStr: str):
    try:
        return timedelta(minutes=float(untilStr))
    except Exception:
        pass

    pattern = r"(?:(\d+)d)?\s*(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?"
    match = re.fullmatch(pattern, untilStr)

    if not match:
        return None

    d, h, m, s = (int(x) if x else 0 for x in match.groups())
    return timedelta(days=d, hours=h, minutes=m, seconds=s)


class Timeout(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Moderation,
        is_dm_only=False,
        is_server_only=True,
        subcommands=None,
        permissions=["`Timeout Members`"],
        help_=None,
        brief="Time outs a member from the server.",
        usage="<target> <date *or* time> <reason[*optional*]>",
        aliases=["to"],
    )

    @commands.command(name="timeout", **Help.to_kwargs)
    async def timeout(
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.User | int | str | None,
        untilStr: str | None,
        *,
        reason: str | None = None,
    ):
        # if user runs the command in dm
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return await ctx.reply("You can only run moderation commands in a server.")

        # if the user has no permission to time out
        if not ctx.author.guild_permissions.moderate_members:
            return await ctx.reply("You have no permission to *time out* Members.")

        # if the bot has no permission to time out
        if not ctx.guild.me.guild_permissions.moderate_members:
            return await ctx.reply("I have no permisson to *time out* Members.")

        # if user doesn't mention any target user
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
            return await ctx.reply(
                f"{user.display_name} is not a Member of this server."
            )

        # if user trys to time out itself
        if target.id == ctx.author.id:
            return await ctx.reply("You can't time out yourself.")

        # if user trys to time out the server owner
        if target.id == ctx.guild.owner_id:
            return await ctx.reply("You can't time out the server *Owner*.")

        # if user trys to time out the bot itself
        if target.id == ctx.me.id:
            return await ctx.reply("You can't time out me hon.")

        # if user trys to time out a bot except the bot
        if target.bot:
            return await ctx.reply("You can't time out poor bots.")

        # if user has lower or equal role position than target
        if (
            target.top_role >= ctx.author.top_role
            and ctx.author.id != ctx.guild.owner_id
        ):
            return await ctx.reply(
                "You can't time out a Member with *higher or equal* role position as you."
            )

        # if the bot has lower or equal role position than target
        if target.top_role >= ctx.guild.me.top_role:
            return await ctx.reply(
                "I can't time out a Member with *higher or equal* role position as me."
            )

        if not untilStr:
            return await ctx.reply(
                "You must specify a time or date, so this Member will be timed out until then. or *false*/*0* to remove the timeout."
            )

        if target.is_timed_out() and untilStr.lower() not in ["false", "0", "remove"]:
            return await ctx.reply(f"{target.display_name} is timed out already.")

        # if entered time was 0, removes the timeout
        if untilStr.lower() in ["false", "0", "remove"]:
            if target.is_timed_out():
                await target.timeout(None, reason=reason)
                await ctx.reply(
                    f"{target.display_name}'s timeout has been *removed* via {ctx.author.display_name}."
                    + (f"\nreason: {reason}" if reason else "")
                )
            else:
                await ctx.reply(
                    f"{target.display_name} had not been timed out at the first place."
                )
            return
        else:
            until = timeDeltaParser(untilStr) or dateparser.parse(untilStr)

        # if entered time wasn't either a datetime or timedelta
        if not until:
            return await ctx.reply("Enter a valid time or date.")

        # if the user didn't enter a time between the supported times
        now = discord.utils.utcnow()
        untilDt = now + until if isinstance(until, timedelta) else until
        untilDt = untilDt.replace(tzinfo=timezone.utc)
        if not (now + timedelta(days=28)) >= untilDt >= now + timedelta(minutes=1):
            return await ctx.reply(
                "Timeout must be at least *60 seconds* or *28 days* at most."
            )

        # time outs the target
        try:
            await target.timeout(untilDt, reason=reason)

            if isinstance(until, timedelta):
                await ctx.reply(
                    f"{target.display_name} has been *timed out* via {ctx.author.display_name} for `{until}`."
                    + (f"\nreason: {reason}" if reason else "")
                )
            else:
                await ctx.reply(
                    f"{target.display_name} has been *timed out* via {ctx.author.display_name} until `{until}` ."
                    + (f"\nreason: {reason}" if reason else "")
                )

        except Exception:
            logger.exception(f".timeout failed to time out:")
            await ctx.reply("Failed to time out.")

    @timeout.error
    async def timeout_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ):
        # if user entered an invalid user
        if isinstance(error, commands.BadArgument):
            await ctx.reply("Member not found. Please mention a valid member.")
        else:
            logger.exception(f"❌ something went wrong with timeout command:")
            await ctx.reply("something went wrong with **timeout**.")

    # timeout slash command
    @app_commands.command(name="timeout", description=Help.brief, extras=Help.extras)
    @app_commands.guild_only()
    @app_commands.describe(
        user="The target member to time out.",
        until="When the member's timeout should expire.",
        reason="The reason to time out the target.",
    )
    async def slashTimeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        until: str,
        reason: str | None = None,
    ):
        # if user runs the command in dm
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You can only run moderation commands in a server.", ephemeral=True
            )

        # if the user has no permission to time out
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                "You have no permission to *time out* Members.", ephemeral=True
            )

        # if the bot has no permission to time out
        if not interaction.guild.me.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                "I have no permisson to *time out* Members.", ephemeral=True
            )

        # if user trys to time out itself
        if user.id == interaction.user.id:
            return await interaction.response.send_message(
                "You can't time out yourself.", ephemeral=True
            )

        # if user trys to time out the server owner
        if user.id == interaction.guild.owner_id:
            return await interaction.response.send_message(
                "You can't time out the server *Owner*.", ephemeral=True
            )

        # if user trys to time out the bot itself
        if user.id == interaction.client.application_id:
            return await interaction.response.send_message(
                "You can't time out me hon.", ephemeral=True
            )

        # if user trys to time out a bot except the bot
        if user.bot:
            return await interaction.response.send_message(
                "You can't time out poor bots.", ephemeral=True
            )

        # if user has lower or equal role position than target
        if (
            user.top_role >= interaction.user.top_role
            and interaction.user.id != interaction.guild.owner_id
        ):
            return await interaction.response.send_message(
                "You can't time out a Member with *higher or equal* role position as you.",
                ephemeral=True,
            )

        # if the bot has lower or equal role position than target
        if user.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                "I can't time out a Member with *higher or equal* role position as me.",
                ephemeral=True,
            )

        if user.is_timed_out() and until.lower() not in ["false", "0", "remove"]:
            return await interaction.response.send_message(
                f"{user.display_name} is timed out already.", ephemeral=True
            )

        # if entered time was 0, removes the timeout
        if until.lower() in ["false", "0", "remove"]:
            if user.is_timed_out():
                await user.timeout(None, reason=reason)
                await interaction.response.send_message(
                    f"{user.display_name}'s timeout has been *removed* via {interaction.user.display_name}."
                    + (f"\nreason: {reason}" if reason else "")
                )
            else:
                await interaction.response.send_message(
                    f"{user.display_name} had not been timed out at the first place.",
                    ephemeral=True,
                )
            return
        else:
            parsedUntil = timeDeltaParser(until) or dateparser.parse(until)

        # if entered time wasn't either a datetime or timedelta
        if not parsedUntil:
            return await interaction.response.send_message(
                "Enter a valid time or date.", ephemeral=True
            )

        # if the user didn't enter a time between the supported times
        now = discord.utils.utcnow()
        untilDt = (
            now + parsedUntil if isinstance(parsedUntil, timedelta) else parsedUntil
        )
        untilDt = untilDt.replace(tzinfo=timezone.utc)
        if not (now + timedelta(days=28)) >= untilDt >= now + timedelta(minutes=1):
            return await interaction.response.send_message(
                "Timeout must be at least *60 seconds* or *28 days* at most.",
                ephemeral=True,
            )

        # time outs the target
        try:
            await user.timeout(untilDt, reason=reason)

            if isinstance(parsedUntil, timedelta):
                await interaction.response.send_message(
                    f"{user.display_name} has been *timed out* via {interaction.user.display_name} for `{until}`."
                    + (f"\nreason: {reason}" if reason else "")
                )
            else:
                await interaction.response.send_message(
                    f"{user.display_name} has been *timed out* via {interaction.user.display_name} until `{until}` ."
                    + (f"\nreason: {reason}" if reason else "")
                )

        except Exception:
            logger.exception(f".timeout failed to time out:")
            await interaction.response.send_message("Failed to time out.")

    @slashTimeout.error
    async def slashTimeout_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        logger.exception(f"❌ something went wrong with /timeout command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **timeout**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **timeout**.", ephemeral=True
            )

    # سکوت 60
    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return

        content = msg.content.strip().split()
        if content[0] != "سکوت":
            return

        if not msg.guild or not isinstance(msg.author, discord.Member):
            return await msg.reply("افراد رو فقط داخل یک سرور میتونید ساکت کنید.")

        if not msg.author.guild_permissions.moderate_members:
            return await msg.reply("شما اجازه *ساکت کردن* کسی را ندارید.")

        if not msg.guild.me.guild_permissions.moderate_members:
            return await msg.reply("من اجازه *ساکت کردن* کسی را ندارم.")

        if not msg.reference or not msg.reference.message_id:
            return

        try:
            refMsg = await msg.channel.fetch_message(msg.reference.message_id)
            target = msg.guild.get_member(refMsg.author.id)
        except discord.NotFound:
            return

        if not target:
            return await msg.reply(
                f"\u202b{refMsg.author.display_name} عضو این سرور نیست.\u202c"
            )

        if target.id == msg.author.id:
            return await msg.reply("نمی توانید خود را ساکت کنید.")

        if target.id == msg.guild.owner_id:
            return await msg.reply("نمی توانید *صاحب* سرور را ساکت کنید.")

        if target.bot and target.id != msg.guild.me.id:
            return await msg.reply("نمی توانید بات های بدبخت بیچاره را ساکت کنید.")

        if target.id == msg.guild.me.id:
            return await msg.reply("نمی توانید من را ساکت کنید.")

        if (
            target.top_role >= msg.author.top_role
            and msg.author.id != msg.guild.owner_id
        ):
            return await msg.reply(
                "نمی توانید عضوی با رول *بالاتر یا برابر* از خودتان را ساکت کنید."
            )

        if target.top_role >= msg.guild.me.top_role:
            return await msg.reply(
                "نمی توانم عضوی با رول *بالاتر یا برابر* از خودم را ساکت کنم."
            )

        if len(content) < 2:
            return await msg.reply(
                "\u202bیک زمان یا تاریخ را مشخص کنید تا این عضو تا آن موقع ساکت شود. و یا *false*/*0* برای برداشتن سکوت.\u202c"
            )

        if target.is_timed_out() and content[1].lower() != "0":
            return await msg.reply(
                f"\u202b{target.display_name} در حال حاضر هم ساکت می باشد.\u202c"
            )

        reason = " ".join(content[2:]) if len(content) > 2 else None

        if content[1] in ["0", "false"]:
            if target.is_timed_out():
                await target.timeout(None, reason=reason)
                await msg.reply(
                    f"\u202bسکوت {target.display_name} برداشته شد.\u202c"
                    + (f"\n\u202bcدلیل: {reason}\u202c" if reason else "")
                )
            else:
                await msg.reply(
                    f"\u202b{target.display_name} از اول هم ساکت نبوده.\u202c"
                )
            return
        else:
            until = timeDeltaParser(content[1]) or dateparser.parse(content[1])

        if not until:
            return await msg.reply("یک زمان یا تاریخ صحیح وارد کنید.")

        # if the user didn't enter a time between the supported times
        now = discord.utils.utcnow()
        untilDt = now + until if isinstance(until, timedelta) else until
        untilDt = untilDt.replace(tzinfo=timezone.utc)
        if not (now + timedelta(days=28) >= untilDt >= now + timedelta(minutes=1)):
            return await msg.reply(
                "زمان سکوت باید حداقل *60 ثانیه* و حداکثر *28 روز* باشد."
            )

        try:
            await target.timeout(untilDt, reason=reason)
            if isinstance(until, timedelta):
                await msg.reply(
                    f"\u202b{target.display_name} به مدت *{until.total_seconds() / 60}* دقیقه ساکت شد.\u202c"
                    + (f"\n\u202bدلیل: {reason}\u202c" if reason else "")
                )
            else:
                await msg.reply(
                    f"\u202b{target.display_name} تا *{until}* ساکت شد.\u202c"
                    + (f"\n\u202bدلیل: {reason}\u202c" if reason else "")
                )
        except Exception:
            logger.exception(f"sokut failed to timeout:")
            await msg.reply("ساکت کردن ناموفق بود.")

        await self.bot.process_commands(msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(Timeout(bot))
