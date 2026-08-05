from discord.ext import commands
import json
from cogs.utility.help import HelpData
from core.logHandler import loggerSetup

logger = loggerSetup(__name__)

with open("config.json") as file:
    config = json.load(file)


class CommandSync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = HelpData(
        category=HelpData.Category.Dev,
        dmOnly=False,
        serverOnly=False,
        subcommands=None,
        permissions=None,
        help=None,
        brief="Syncs and updates slash commands.",
        usage=None,
        aliases=["csync"],
    )

    @commands.command(name="commandsync", hidden=True, **Help.to_kwargs)
    async def commandsync(self, ctx: commands.Context[commands.Bot]):
        inGuild = True if ctx.guild else False

        # checks if the user is an admin to use the command
        if str(ctx.author.id) not in config["ADMINS"]:
            msg = await ctx.reply("You can't use this command.")
            if inGuild:
                await msg.delete(delay=5)
                await ctx.message.delete()
            return

        syncedCmds = await self.bot.tree.sync()
        syncedCmds = [("/" + cmd.name) for cmd in syncedCmds]
        print("\n--------------")
        print(f"{syncedCmds} commands have been synced. ✔️")
        msg = await ctx.reply("All slash commands have been synced.")
        if inGuild:
            await msg.delete(delay=5)
            await ctx.message.delete(delay=5)
            return

    @commandsync.error
    async def commandsync_error(
        self, ctx: commands.Context[commands.Bot], error: Exception
    ):
        logger.exception(f"❌ something went wrong with commandsync command:")
        await ctx.reply("something went wrong with **commandsync**.", delete_after=5)


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandSync(bot))
