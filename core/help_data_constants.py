"""Contains help datas for every command."""

from __future__ import annotations

__all__ = [
    "ADJUSTBALANCE_HELP",
    "BALANCE_HELP",
    "BLACKJACK_HELP",
    "CALCULATE_HELP",
    "CHOOSE_HELP",
    "DAILY_HELP",
    "HELP_HELP",
    "LIMITDICE_HELP",
    "PING_HELP",
    "SAY_HELP",
    "WHISPER_HELP",
]

from core.help import HelpData

ADJUSTBALANCE_HELP = HelpData(
    is_enabled=False,
    name="adjustbalance",
    category=HelpData.CommandCategory.DEV,
    is_dm_only=False,
    is_server_only=False,
    subcommands=["deposit", "withdraw", "set"],
    permissions=None,
    help_=None,
    brief="idk",
    usage=None,
    aliases=["abalance", "adjbal", "adjustb"],
    is_hidden=True,
)


BALANCE_HELP = HelpData(
    is_enabled=True,
    name="balance",
    category=HelpData.CommandCategory.ECONOMY,
    is_dm_only=False,
    is_server_only=False,
    subcommands=None,
    permissions=None,
    help_=None,
    brief="Shows the balance of the user.",
    usage=None,
    aliases=["bal"],
    is_hidden=False,
)

BLACKJACK_HELP = HelpData(
    is_enabled=True,
    name="blackjack",
    category=HelpData.CommandCategory.GAMES,
    is_dm_only=False,
    is_server_only=False,
    subcommands=None,
    permissions=None,
    help_=(
        "A card game where you compete against the dealer."
        " Your goal is to have a hand value closer to 21"
        " than the dealer's without going over 21."
        "\n\nCard values:"
        "\n2-10: Worth their face value."
        "\nK, Q, J, 10: Worth 10 points."
        "\nA: Worth 11 points by default, but is automatically counted as 1"
        " whenever counting it as 11 would cause the hand to bust."
        "\n\n1. You and the dealer are each dealt two initial cards. One of the"
        " dealer's cards is face up, while the other"
        " remains hidden as the hole card."
        "\n2. If the dealer's upcard is an Ace, you'll"
        " be offered the option to place"
        " an Insurance side bet before play continues."
        "\n3. On your turn choose `Hit` to draw another card, `Stand` to"
        " end your turn, `Double Down` to double your bet and receive"
        " exactly one more card or `Surrender` to end the game immediately and"
        " forfeit half of your bet."
        "\n4. If your hand exceeds 21, you `Bust` and immediately lose"
        " the game and lose your bet."
        "\n5. Once your turn ends, the dealer reveals the hole card and keeps"
        " hitting until reaching 17 or higher."
        "\n6. If the dealer busts, you win an amount equal to your bet."
        " Otherwise, the hand closest"
        " to 21 wins. If both hands have the same value, the round ends"
        " in a `Push` and your bet is returned."
        "\n\nNote: `Surrender` and `Double Down` can only be done before taking"
        " any other action (Hit and Stand)."
        "\n\nNote: Insurance will be offered only when the dealer's upcard is an"
        " Ace. You may place a side bet of up to half your original bet. If"
        " the dealer has Blackjack, Insurance pays 2:1."
        " Otherwise, the Insurance bet is lost and the round continues."
        "\n\nNote: When the dealer's upcard is Ace or any 10-value card,"
        " the dealer peeks at"
        " the hole card; If the hole card makes the dealer's hand a"
        " `Blackjack`, the dealer wins immediately and the player loses"
        " unless they also have Blackjack which ends in a `Push`"
        " and the player's bet will be returned. The Insurance bet is resolved"
        " immediately after the dealer peeks at the hole card."
        "\n\nNote: If the player is dealt a Blackjack, they immediately win the"
        " game unless the dealer also has Blackjack."
    ),
    brief="The traditional Blackjack game.",
    usage="<bet_amount[*optional*]>",
    aliases=["bj", "blackj"],
    is_hidden=False,
)

CALCULATE_HELP = HelpData(
    is_enabled=False,
    name="calculate",
    category=HelpData.CommandCategory.UTILITY,
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
    aliases=["calc"],
    is_hidden=False,
)

CHOOSE_HELP = HelpData(
    is_enabled=True,
    name="choose",
    category=HelpData.CommandCategory.UTILITY,
    is_dm_only=False,
    is_server_only=False,
    subcommands=None,
    permissions=None,
    help_=None,
    brief="Chooses one option between given choices",
    usage='<count[*optional*]> <choices(separated with "|")>',
    aliases=None,
    is_hidden=False,
)

DAILY_HELP = HelpData(
    is_enabled=True,
    name="daily",
    category=HelpData.CommandCategory.ECONOMY,
    is_dm_only=False,
    is_server_only=False,
    subcommands=None,
    permissions=None,
    help_=None,
    brief="Claims the Daily Reward for the user.",
    usage=None,
    aliases=["d"],
    is_hidden=False,
)

HELP_HELP = HelpData(
    is_enabled=True,
    name="help",
    category=HelpData.CommandCategory.UTILITY,
    is_dm_only=False,
    is_server_only=False,
    subcommands=None,
    permissions=None,
    help_=(
        "Displays the help menu for Amélie."
        "\n\nWithout a command name, this command shows all available commands"
        " organized by category."
        "\n\nProvide a command name to view detailed information, including its"
        " description, usage, aliases, required permissions, subcommands, and"
        " whether it can only be used in direct messages or servers."
    ),
    brief="Displays the help menu or detailed information about a command.",
    usage="<command_name*[optional]*>",
    aliases=["h"],
    is_hidden=False,
)

LIMITDICE_HELP = HelpData(
    is_enabled=True,
    name="limitdice",
    category=HelpData.CommandCategory.GAMES,
    is_dm_only=False,
    is_server_only=False,
    subcommands=None,
    permissions=None,
    help_=(
        "A game between two players; All about luck and will."
        "\nBoth players take turns rolling their die. and they can't see each other's"
        " hand."
        "\nAny roll from **one to five** worths **1 point**."
        "\nThey can then keep rolling to increase their score."
        "\n**If anyone rolls a six, their final score is 0** and they can't gain any"
        " more points at that time."
        "\nIf anyone feels they'll roll a six, they can declare Stop. and so their"
        " score is frozen in place."
        "\nIf both players stop or roll a six, the top scorer wins."
        "\n\nHowever, rolling a six doesn't mean an instant loss! you can keep rolling"
        " that die."
        "\nYou won't gain any more points but your opponent will think you're still"
        " racking them up."
        "\n\nIf your opponent keep rolling their die, never stopping.., it'll make you"
        " wonder if they rolled a six or not."
        "\nShould you stop or not? You'll need to think about that, all the way to your"
        " Limits, in this **test of Willpower!**"
    ),
    brief="A two-player dice game of luck, bluffing, and willpower where rolling a six"
    " can change everything.",
    usage="<target[*optional*]>",
    aliases=["lm"],
    is_hidden=False,
)

PING_HELP = HelpData(
    is_enabled=True,
    name="ping",
    category=HelpData.CommandCategory.UTILITY,
    is_dm_only=False,
    is_server_only=False,
    subcommands=None,
    permissions=None,
    help_=(
        "Checks Amelies conenction speed by measuring WebSocket Latency"
        " (which is the delay between bots server and Discord Gateway) and Bot Latency"
        " (which is the time it takes Amélie to send a message and recieve a response)."
    ),
    brief="Pings Amélie.",
    usage=None,
    aliases=None,
    is_hidden=False,
)

SAY_HELP = HelpData(
    is_enabled=True,
    name="say",
    category=HelpData.CommandCategory.UTILITY,
    is_dm_only=False,
    is_server_only=False,
    subcommands=None,
    permissions=None,
    help_=(
        "Says the given message in the desired channel. But first, it checks if the"
        " user(and Amélie herself) have the propper permission to say or send something"
        " in the target channel."
        "\nThis also works in DM and Group channels."
    ),
    brief="Says something in a channel.",
    usage='<target channel *or* "here"> <message>',
    aliases=["echo"],
    is_hidden=False,
)

WHISPER_HELP = HelpData(
    is_enabled=True,
    name="whisper",
    category=HelpData.CommandCategory.UTILITY,
    is_dm_only=False,
    is_server_only=True,
    subcommands=None,
    permissions=None,
    help_="Whispers a message to a member. use this command to talk with a member"
    " privately inside a server.",
    brief="Whispers something to a member.",
    usage="<target> <message>",
    aliases=["wh"],
    is_hidden=False,
)
