import discord
import sympy as sp
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class Calc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Utility,
        is_dm_only=False,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=(
            "Calculates the given math expression."
            "\nsupports trigonometric, logarithms and etc."
        ),
        brief="Calculates the given math expression.",
        usage="<math_expression>",
        aliases=["calculator", "calculate"],
    )

    @commands.command(name="calc", **Help.to_kwargs)
    async def calc(
        self, ctx: commands.Context[commands.Bot], *, expression: str | None = None
    ):
        if not expression:
            return await ctx.reply("You must enter a math expression to be calculated.")

        try:
            expression = expression.replace("^", "**")
            expression = expression.replace("√", "sqrt")

            result = sp.sympify(  # type: ignore
                expression,
                locals={  # type: ignore
                    "pi": sp.pi,
                    "e": sp.E,
                    "sin": sp.sin,
                    "cos": sp.cos,
                    "tan": sp.tan,
                    "cot": sp.cot,
                    "sec": sp.sec,
                    "csc": sp.csc,
                    "asin": sp.asin,
                    "acos": sp.acos,
                    "atan": sp.atan,
                    "acot": sp.acot,
                    "asec": sp.asec,
                    "acsc": sp.acsc,
                    "sinh": sp.sinh,
                    "cosh": sp.cosh,
                    "tanh": sp.tanh,
                    "coth": sp.coth,
                    "sech": sp.sech,
                    "csch": sp.csch,
                    "asinh": sp.asinh,
                    "acosh": sp.acosh,
                    "atanh": sp.atanh,
                    "acoth": sp.acoth,
                    "asech": sp.asech,
                    "acsch": sp.acsch,
                    "log": sp.log,
                    "sqrt": sp.sqrt,  # type: ignore
                },
            )

            # Converts symbolic to numeric if needed
            numeric_result = (
                result.evalf() if result.is_real or result.is_complex else result
            )  # type: ignore

            await ctx.reply(f"= `{numeric_result:.2f}`")
        except Exception:
            await ctx.reply("Enter a valid math expression.")

    @calc.error
    async def calc_error(self, ctx: commands.Context[commands.Bot], error: Exception):
        logger.exception(f"❌ something went wrong with calc command:")
        await ctx.reply("something went wrong with **calc**.")

    # calc slash command
    @app_commands.command(name="calc", description=Help.brief, extras=Help.extras)
    @app_commands.describe(
        expression="The expression to be calculated.",
        hidden="Whether the result should be vsible only to you or not.",
    )
    async def slashCalc(
        self, interaction: discord.Interaction, expression: str, hidden: bool = False
    ):
        await interaction.response.defer()
        expression = expression.replace("^", "**")
        expression = expression.replace("√", "sqrt")

        try:
            result = sp.sympify(  # type: ignore
                expression,
                locals={
                    "pi": sp.pi,
                    "e": sp.E,
                    "sin": sp.sin,
                    "cos": sp.cos,
                    "tan": sp.tan,
                    "cot": sp.cot,
                    "sec": sp.sec,
                    "csc": sp.csc,
                    "asin": sp.asin,
                    "acos": sp.acos,
                    "atan": sp.atan,
                    "acot": sp.acot,
                    "asec": sp.asec,
                    "acsc": sp.acsc,
                    "sinh": sp.sinh,
                    "cosh": sp.cosh,
                    "tanh": sp.tanh,
                    "coth": sp.coth,
                    "sech": sp.sech,
                    "csch": sp.csch,
                    "asinh": sp.asinh,
                    "acosh": sp.acosh,
                    "atanh": sp.atanh,
                    "acoth": sp.acoth,
                    "asech": sp.asech,
                    "acsch": sp.acsch,
                    "log": sp.log,
                    "sqrt": sp.sqrt,  # type: ignore
                },
            )
        except Exception:
            return await interaction.followup.send(
                "Enter a valid math expression.", ephemeral=True
            )

        # Converts symbolic to numeric if needed
        numeric_result = (
            result.evalf() if result.is_real or result.is_complex else result
        )  # type: ignore

        await interaction.followup.send(f"= `{numeric_result:.2f}`", ephemeral=hidden)

    @slashCalc.error
    async def slashCalc_error(self, interaction: discord.Interaction, error: Exception):
        logger.exception(f"❌ something went wrong with /calc command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **calc**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **calc**.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Calc(bot))
