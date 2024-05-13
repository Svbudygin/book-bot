from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from sqlalchemy import ScalarResult
from db_api import Channel, Group


class MenuAction(CallbackData, prefix="menu"):
    action: str


class EntryAction(CallbackData, prefix="entry"):
    action: str
    entry_id: int


class ItemAction(CallbackData, prefix="item"):
    action: str
    isbn: str


def build_inline_keyboard_markup(*rows: dict[str, CallbackData]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for row in rows:
        buttons.append([])
        for text, callback_data in row.items():
            buttons[-1].append(InlineKeyboardButton(text=text, callback_data=callback_data.pack()))
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_channel_list_markup(channels: ScalarResult[Channel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for channel in channels:
        worksheet_title: str = ""
        if channel.worksheet_title is not None:
            worksheet_title = channel.worksheet_title
        builder.button(text=f"{channel.title} ({worksheet_title})", callback_data=EntryAction(action="show_channel_menu", entry_id=channel.id))
    builder.button(text="➕ Добавить канал", callback_data=MenuAction(action="ask_new_channel_message"))
    builder.adjust(1, repeat=True)
    return builder.as_markup()


def build_channel_menu_markup(channel: Channel) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📣 Заполнить канал", callback_data=MenuAction(action="publish_from_worksheet"))
    builder.button(text="⚠️ Забыть канал", callback_data=MenuAction(action="delete_channel"))
    builder.button(text="« Назад", callback_data=MenuAction(action="show_channel_list"))
    builder.adjust(1, repeat=True)
    return builder.as_markup()


def build_dialogue_markup(state: str) -> InlineKeyboardMarkup:
    markup: InlineKeyboardMarkup | None = None
    match state.split(":")[1]:
        case "NewChannelMessage":
            markup = build_inline_keyboard_markup(
                {"« Назад": MenuAction(action="show_channel_list")}
            )
        case "GroupMessage":
            markup = build_inline_keyboard_markup(
                {"✅ Готово": MenuAction(action="end_dialogue")}
            )
    return markup


# def build_item_markup(isbn: str) -> InlineKeyboardMarkup:
#     return build_inline_keyboard_markup(
#         {"Заказать": ItemAction(action="order", isbn=isbn), "Отменить": ItemAction(action="cancel_order", isbn=isbn)}
#     )

def build_item_markup(isbn: str) -> InlineKeyboardMarkup:
    keyboard = []
    actions = {
        "Заказать в Европу": ItemAction(action="orderEU", isbn=isbn),
        "Заказать в РФ": ItemAction(action="orderRF", isbn=isbn),
        "Отменить в РФ": ItemAction(action="cancel_orderRF", isbn=isbn),
        "Отменить в Европу": ItemAction(action="cancel_orderEU", isbn=isbn)
    }

    for text, action in actions.items():
        # Create a list with a single button for each row
        row = [InlineKeyboardButton(text=text, callback_data=action.pack())]
        keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

