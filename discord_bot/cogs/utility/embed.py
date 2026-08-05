import datetime
import re
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)


def parse_args(args: str):
    matches: list[tuple[str, str]] = re.findall(r"(\w+)\s*:\s*\((.*?)\)", args)
    return matches if matches else None


def colorValidation(value: str):
    # removes leading '#' if any
    value = value.lstrip("#")

    # ensure that the hex code is 3 or 6 characters to be valid
    if len(value) not in [6, 3]:
        return False

    return bool(re.fullmatch(r"[0-9a-fA-F]{3}|[0-9a-fA-F]{6}", value))


def urlValidation(url: str):
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except:
        return False


async def respond(
    ctx: commands.Context[commands.Bot] | discord.Interaction,
    msg: str,
    ephem: bool = True,
):
    if isinstance(ctx, discord.Interaction):
        return await ctx.response.send_message(msg, ephemeral=ephem)
    else:
        return await ctx.reply(msg)


async def assignVars(
    ctx: commands.Context[commands.Bot] | discord.Interaction,
    arg_list: list[tuple[str, str]],
):
    data: dict[str, None | str | discord.Color | datetime.datetime] = {
        "title": None,
        "desc": None,
        "url": None,
        "color": None,
        "imgurl": None,
        "thumbnailurl": None,
        "author": None,
        "authorurl": None,
        "authoriconurl": None,
        "footer": None,
        "footericonurl": None,
        "timestamp": None,
    }
    for arg, value in arg_list:
        arg = arg.lower()
        if arg == "title":
            if len(value) > 256:
                await respond(ctx, msg=f"`{arg}` can only be up to **256** characters.")
                return None
            data["title"] = value

        elif arg in ["desc", "description"]:
            if len(value) > 4096:
                await respond(
                    ctx, msg=f"`{arg}` can only be up to **4096** characters."
                )
                return None
            data["desc"] = value

        elif arg == "url":
            if urlValidation(value):
                data["url"] = value
            else:
                await respond(
                    ctx,
                    msg=f"enter a valid **url** for `{arg}` (like 'https://example.com').",
                )
                return None

        elif arg in ["color", "colour"]:
            if colorValidation(value):
                if not str(value).startswith("#"):
                    value = f"#{value}"
                data["color"] = discord.Color.from_str(value)
            else:
                await respond(
                    ctx, msg=f"enter a valid **hex code** for `{arg}` (like '#ffffff')."
                )
                return None

        elif arg in ["image url", "imageurl", "imgurl", "image_url"]:
            if urlValidation(value):
                data["imgurl"] = value
            else:
                await respond(
                    ctx,
                    msg=f"enter a valid **url** for `{arg}` (like 'https://example.com').",
                )
                return None

        elif arg in ["thumbnail url", "thumbnailurl", "thumbnail_url"]:
            if urlValidation(value):
                data["thumbnailurl"] = value
            else:
                await respond(
                    ctx,
                    msg=f"enter a valid **url** for `{arg}` (like 'https://example.com').",
                )
                return None

        elif arg in ["author", "author name", "authorname"]:
            if len(value) > 256:
                await respond(ctx, msg=f"`{arg}` can only be up to **256** characters.")
                return None
            data["author"] = value

        elif arg in ["authorurl", "author url", "author_url"]:
            if urlValidation(value):
                data["authorurl"] = value
            else:
                await respond(
                    ctx,
                    msg=f"enter a valid **url** for `{arg}` (like 'https://example.com').",
                )
                return None

        elif arg in ["authoriconurl", "author icon url", "author_icon_url"]:
            if urlValidation(value):
                data["authoriconurl"] = value
            else:
                await respond(
                    ctx,
                    msg=f"enter a valid **url** for `{arg}` (like 'https://example.com').",
                )
                return None

        elif arg == "footer":
            if len(value) > 2048:
                await respond(
                    ctx, msg=f"`{arg}` can only be up to **2048** characters."
                )
                return None
            data["footer"] = value

        elif arg in ["footericonurl", "footer icon url", "footer_icon_url"]:
            if urlValidation(value):
                data["footericonurl"] = value
            else:
                await respond(
                    ctx,
                    msg=f"enter a valid **url** for `{arg}` (like 'https://example.com').",
                )
                return None

        elif arg in ["timestamp", "ts"]:
            if value.lower() in ["yes", "y", "true", "now"]:
                data["timestamp"] = discord.utils.utcnow()

            elif value.lower() in ["no", "n", "false"]:
                pass

            else:
                await respond(ctx, msg=f"you must select **yes/no** for `{arg}`.")
                return None

        else:
            await respond(ctx, msg=f"{arg} is not a valid argument.")
            return None

    return data  # returns the data dictionary if no problems else None is returned


class Embed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Utility,
        is_dm_only=False,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=(
            "This command can sends or edits an embed in the channel."
            "\nYou can specify Embed attributes like `key: (value)` (title: (hi) for instance). Supports all kind of Embed attributes."
        ),
        brief="Sends an Embed in the channel.",
        usage="<embed argument 1> <embed argument 2> <embed argument ..>",
        aliases=None,
    )

    @commands.command(name="embed", **Help.to_kwargs)
    async def embed(
        self, ctx: commands.Context[commands.Bot], *, args: str | None = None
    ):
        # if user doesn't enter the arguments
        if not args:
            return await ctx.reply(
                "You must enter at least one argument to create the Embed."
            )

        argList = parse_args(args)  # parsing args
        if not argList:
            return await ctx.reply("enter valid forms of arguments.")

        data = await assignVars(ctx, argList)  # collecting the data from args
        if not data:
            return

        # creates the embed with the fetched data
        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("desc"),
            url=data.get("url"),
            color=data["color"] if isinstance(data["color"], discord.Color) else None,
            timestamp=(
                data["timestamp"]
                if isinstance(data["timestamp"], datetime.datetime)
                else None
            ),
        )
        if data.get("footer"):
            embed.set_footer(
                text=data.get("footer"), icon_url=data.get("footericonurl")
            )
        if data.get("author"):
            embed.set_author(
                name=data.get("author"),
                url=data.get("authorurl"),
                icon_url=data.get("authoriconurl"),
            )
        if data.get("imgurl"):
            embed.set_image(url=data.get("imgurl"))
        if data.get("thumbnailurl"):
            embed.set_thumbnail(url=data.get("thumbnailurl"))

        await ctx.send(embed=embed)

    @embed.error
    async def embed_error(self, ctx: commands.Context[commands.Bot], error: Exception):
        logger.exception(f"❌ something went wrong with embed command:")
        await ctx.reply(f"something went wrong with **embed**.")

    # embed slash command
    @app_commands.command(name="embed", description=Help.brief, extras=Help.extras)
    async def slashEmbed(
        self,
        interaction: discord.Interaction,
        title: str | None = None,
        description: str | None = None,
        url: str | None = None,
        color: str | None = None,
        image_url: str | None = None,
        thumbnail_url: str | None = None,
        author: str | None = None,
        author_url: str | None = None,
        author_icon_url: str | None = None,
        footer: str | None = None,
        footer_icon_url: str | None = None,
        timestamp: bool = False,
    ):

        argList = [
            (name, value)
            for name, value in locals().items()
            if name not in ["self", "interaction", "timestamp"] and value
        ]
        if not argList:
            return await interaction.response.send_message(
                "You must enter at least one argument to create the Embed.",
                ephemeral=True,
            )

        data = await assignVars(interaction, argList)  # collecting the data from args

        # returns if no data is available
        if not data:
            return

        # creates the embed with the fetched data
        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("desc"),
            url=data.get("url"),
            color=data["color"] if isinstance(data["color"], discord.Color) else None,
            timestamp=discord.utils.utcnow() if timestamp else None,
        )
        if data.get("footer"):
            embed.set_footer(
                text=data.get("footer"), icon_url=data.get("footericonurl")
            )
        if data.get("author"):
            embed.set_author(
                name=data.get("author"),
                url=data.get("authorurl"),
                icon_url=data.get("authoriconurl"),
            )
        if data.get("imgurl"):
            embed.set_image(url=data.get("imgurl"))
        if data.get("thumbnailurl"):
            embed.set_thumbnail(url=data.get("thumbnailurl"))

        await interaction.response.send_message(embed=embed)

    @slashEmbed.error
    async def slashEmbed_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        logger.exception(f"❌ something went wrong with /embed command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **embed**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **embed**.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Embed(bot))
