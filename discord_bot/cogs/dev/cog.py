import json

from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)

with open("config.json") as file:
    config = json.load(file)


class StartUp(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Dev,
        is_dm_only=False,
        is_server_only=False,
        subcommands=["reload", "list"],
        permissions=None,
        help_=(
            "A Cog handling command made for developers of the bot."
            "\n\n-`reload`: This subcommand is used when trying to reload a cog without disconnecting and connecting bot again. (aliases: `r`)"
            "\n\n-`list`: Prints every each available cog's name in the console."
        ),
        brief="Cog moderation command.",
        usage="<subcommand> <cog_name[*optional*]>",
        aliases=None,
        is_hidden=True,
    )

    @commands.command(name="cog", hidden=True, **Help.to_kwargs)
    async def cog(
        self,
        ctx: commands.Context[commands.Bot],
        cmd: str | None,
        extension: str | None = None,
    ):
        inGuild = True if ctx.guild else False

        # checks if the user is an admin to use the command
        if str(ctx.author.id) not in config["ADMINS"]:
            msg = await ctx.reply("You can't use this command.")
            if inGuild:
                await msg.delete(delay=5)
                await ctx.message.delete()
            return

        # if user entered no subcommand
        if not cmd:
            msg = await ctx.reply("You must enter a subcommand for this command.")
            if inGuild:
                await msg.delete(delay=5)
                await ctx.message.delete(delay=5)
            return

        cmd = cmd.lower()
        extension = extension.lower() if extension else None

        extensionList = list(self.bot.extensions)  # stores all registered extentions

        # reload subcommand
        if cmd in ("reload", "r"):
            # reloads all cogs if no extension is given
            if not extension or extension == "all":
                msg = await ctx.reply("Reloading all cogs..")
                print("\n--------------")

                for ext in extensionList:
                    await self.bot.reload_extension(ext)
                    print(f"🔄️ {ext.split('.')[-1]} reloaded.")

                await msg.edit(content="All cogs have been reloaded succesfully. ✅")

            # reloads the given extention
            else:
                match = None
                # if given extention is found in registered cogs, stops searching
                for ext in extensionList:
                    if ext.split(".")[-1] == extension:
                        match = ext
                        break

                # if no match was found, notifys the user
                if not match:
                    msg = await ctx.reply(f"`{extension}` is not a loaded cog.")
                    if inGuild:
                        await msg.delete(delay=5)
                        await ctx.message.delete(delay=5)
                    return

                # reloads the matched extention
                msg = await ctx.reply(f"Reloading `{match.split('.')[-1]}` cog..")
                print("\n--------------")

                await self.bot.reload_extension(match)
                print(f"🔄️ {match.split('.')[-1]} cog is reloaded.")

                await msg.edit(
                    content=f"`{match.split('.')[-1]}` cog has been reloaded succesfully. ✅"
                )

            if inGuild:
                await msg.delete(delay=5)
                await ctx.message.delete()

        # list subcommand
        elif cmd == "list":
            print(f"\n--------------\n{extensionList}")
            msg = await ctx.reply(content="Cogs list has been sent to the console. ✅")
            if inGuild:
                await msg.delete(delay=5)
                await ctx.message.delete(delay=5)

        # invalid subcommand
        else:
            msg = await ctx.reply(content="Enter a valid subcommand.")
            if inGuild:
                await msg.delete(delay=5)
                await ctx.message.delete(delay=5)

    @cog.error
    async def cog_error(self, ctx: commands.Context[commands.Bot], error: Exception):
        logger.exception(f"❌ something went wrong with cog command:")
        await ctx.reply("something went wrong with **cog**.", delete_after=5)


async def setup(bot: commands.Bot):
    await bot.add_cog(StartUp(bot))
