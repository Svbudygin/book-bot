from aiogram.filters.state import State, StatesGroup


class MenuState(StatesGroup):
    Menu = State()


class Dialogue(StatesGroup):
    NewChannelMessage = State()
    WorksheetTitle = State()
    GroupMessage = State()
    row_number = State()

