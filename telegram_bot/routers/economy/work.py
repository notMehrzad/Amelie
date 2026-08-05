import random
from aiogram import Router, types, filters, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from database import db, eco
from datetime import timedelta, datetime, timezone
from cogs.economy.daily import tdFormatter
from telegramRouters.utility.help import HelpData

router = Router(name=__name__)


class Sudoku:
    """
    The class that represents a sudoku puzzle.
    """

    def __init__(self):
        self.sudo = self.sudoGenerator()

    def sudoGenerator(self):
        sudo: list[list[int]] = []

        sudo.append([])
        sudo.append([])
        jstart = 0
        jend = 3
        for _ in range(2):
            cageNumbers: list[int] = []
            for i in range(2):
                for j in range(jstart, jend):
                    allowedNumbers = [
                        n
                        for n in range(1, 7)
                        if n not in cageNumbers
                        and n not in sudo[i]
                        and n not in [r[j] for r in sudo if sudo.index(r) < i]
                    ]
                    choice = random.choice(allowedNumbers)
                    sudo[i].append(choice)
                    cageNumbers.append(choice)
            jstart += 3
            jend += 3

        self.leftyIndex = (random.randint(0, 1), random.randint(0, 2))
        self.rightyIndex = (random.randint(0, 1), random.randint(3, 5))

        self.lefty = sudo[self.leftyIndex[0]][self.leftyIndex[1]]
        sudo[self.leftyIndex[0]][self.leftyIndex[1]] = 0
        self.righty = sudo[self.rightyIndex[0]][self.rightyIndex[1]]
        sudo[self.rightyIndex[0]][self.rightyIndex[1]] = 0

        return sudo

    def setLefty(self, n: int):
        if n == self.lefty:
            self.sudo[self.leftyIndex[0]][self.leftyIndex[1]] = self.lefty
        else:
            raise ValueError("Incorrect lefty value.")

    def setRighty(self, n: int):
        if n == self.righty:
            self.sudo[self.rightyIndex[0]][self.rightyIndex[1]] = self.righty
        else:
            raise ValueError("Incorrect righty value.")

    def __str__(self):
        sudoStr: list[str] = []
        for i in self.sudo:
            sudoStr.append(
                " ".join(
                    (
                        f"{i[j] if i[j] else 'X'}"
                        if j != 3
                        else f"| {i[j] if i[j] else 'X'}"
                    )
                    for j in range(6)
                )
            )
        return sudoStr[0] + "\n" + sudoStr[1]


HelpData = HelpData(
    category=HelpData.Category.Economy,
    dmOnly=False,
    serverOnly=False,
    subcommands=None,
    permissions=None,
    help=None,
    brief="Works, i guess",
    usage=None,
    aliases=None,
)


@router.message(filters.Command("work", *HelpData.aliases, ignore_case=True))
async def work(message: types.Message):
    # checks the balance and the last work date of the user
    if message.from_user:
        row = await db.fetchone(
            """
            SELECT balance, last_work_date FROM user
            WHERE user_id = ?;
            """,
            (message.from_user.id,),
        )
        # if user has no economy account
        if not row:
            return await message.answer(
                "You have no account to work for.\nTry `/daily` to get your first daily and account and try again."
            )

        now = datetime.now(timezone.utc)

        workDate: datetime | None = (
            datetime.fromisoformat(row["last_work_date"])
            if isinstance(row["last_work_date"], str)
            else row["last_work_date"]
        )
        # if user trys to work within the limited time
        if workDate and workDate + timedelta(minutes=90) > now:
            return await message.answer(
                f"You must rest `{tdFormatter(workDate + timedelta(minutes=90) - now)}` to be able to `work` again."
            )

        view = WorkView(message, userBalance=row["balance"])
        await view.start()


class ButtonCallback(CallbackData, prefix="work"):
    user_id: int
    type: str
    value: int


class WorkView:
    timeout = 90

    def __init__(
        self,
        message: types.Message,
        *,
        userBalance: int,
    ):
        self.message = message
        if message.from_user:
            self.user = message.from_user
        self.userBalance = userBalance
        self.timestamp = datetime.now(timezone.utc)
        self.sudo = Sudoku()
        self.expiresAt = datetime.now(timezone.utc) + timedelta(
            seconds=WorkView.timeout
        )

        n = [i for i in range(1, 7)]
        leftyBtnsList = [
            n.pop(self.sudo.lefty),
            *random.sample(n, 2),
        ]  # creates random buttons for the left X in sudoku containing the answer
        random.shuffle(leftyBtnsList)  # shuffles the options
        n = [i for i in range(1, 7)]
        rightyBtnsList = [
            n.pop(self.sudo.righty),
            *random.sample(n, 2),
        ]  # creates random buttons for the right X in sudoku containing the answer
        random.shuffle(rightyBtnsList)  # shuffles the options

        # creates and attachs the left buttons
        self.leftyBtns = InlineKeyboardBuilder()
        for i in leftyBtnsList:
            self.leftyBtns.button(
                text=str(i),
                callback_data=ButtonCallback(
                    user_id=self.user.id, type="lefty", value=i
                ),
            )
        self.leftyBtns.adjust(3)

        self.rightyBtns = InlineKeyboardBuilder()
        # creates and attachs new buttons
        for i in rightyBtnsList:
            self.rightyBtns.button(
                text=str(i),
                callback_data=ButtonCallback(
                    user_id=self.user.id, type="righty", value=i
                ),
            )
        self.rightyBtns.adjust(3)

    async def start(self):
        self.message.answer(
            text=(
                f"Work ⛏️\n\nSolve this Sudoku puzzle to earn your fee.\n\n{self.sudo}"
            ),
            reply_markup=self.leftyBtns.as_markup(),
        )  # sends the initial message
        self.leftyBtnsCallback()

    def leftyBtnsCallback(self):
        @router.callback_query(ButtonCallback.filter(F.type == "lefty"))
        async def callback(
            callback: types.CallbackQuery, callback_data: ButtonCallback
        ):
            await callback.answer()

            # checks that only the user can interact with the buttons
            if callback.from_user.id != callback_data.user_id:
                return await callback.answer(
                    "You can't work for others.", show_alert=True
                )

            if datetime.now(timezone.utc) > self.expiresAt:
                return await self.on_timeout()

            # if user chooses the wrong option
            if callback_data.value != self.sudo.lefty:
                return await callback.answer("Wrong ! ❌", show_alert=True)

            self.sudo.setLefty(callback_data.value)  # sets the left X answer
            await callback.message.edit_text(  # type: ignore
                text=(
                    "Work ⛏️"
                    "\n\nSolve this Sudoku puzzle to earn your fee."
                    f"\n\n{self.sudo}"
                ),
                reply_markup=self.rightyBtns.as_markup(),
            )
            self.rightyBtnsCallback()

        return callback

    def rightyBtnsCallback(self):
        @router.callback_query(ButtonCallback.filter(F.type == "righty"))
        async def callback(
            callback: types.CallbackQuery, callback_data: ButtonCallback
        ):
            await callback.answer()

            # checks that only the user can interact with the buttons
            if callback.from_user.id != callback_data.user_id:
                return await callback.answer(
                    "You can't work for others.", show_alert=True
                )

            if datetime.now(timezone.utc) > self.expiresAt:
                return await self.on_timeout()

            # if user chooses the wrong option
            if callback_data.value != self.sudo.righty:
                return await callback.answer("Wrong ! ❌", show_alert=True)

            self.sudo.setRighty(callback_data.value)  # sets the right X answer

            await db.execute(
                """
                UPDATE user
                SET balance = ?, last_work_date = ?
                WHERE user_id = ?;
                """,
                (self.userBalance + eco.work, self.timestamp, self.user.id),
            )  # updates the user balance

            await callback.message.edit_text(  # type: ignore
                text=(
                    "Work ⛏️"
                    "\n\nGood Job !"
                    f"\nYou earned **{eco.work}** for working so hard."
                    f"You must rest **{tdFormatter(timedelta(minutes=90))}** to fully recover and be able to work again."
                ),
                reply_markup=None,
            )  # sends the result

        return callback

    async def on_timeout(self):
        await self.message.edit_text(
            text=("Work ⛏️\n\n⏰ You quited your work too early honey."),
            reply_markup=None,
        )
