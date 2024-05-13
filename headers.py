from datetime import datetime, timezone, timedelta
from itertools import groupby
from operator import attrgetter
from sqlalchemy import ScalarResult
from db_api import Channel, Group, Item, Order
from sheets_api import Record


def build_channel_header(channel: Channel, groups: ScalarResult[Group]) -> str:
    header = f"<b>Канал: {channel.title}</b>"
    if channel.worksheet_title is not None:
        header += f"\n\n<b>Лист:</b> <code>{channel.worksheet_title}</code>"
    header += f"\n\n<b>Группы:</b>"
    for group in groups:
        header += f" <code>{group.title}</code>"
    return header


def build_item_header(record: Record) -> str:
    header = f"<b>{record.title}</b>"
    
    header += f"\n\n<b>Цена</b>\n{record.price_rub} ₽\n{record.price_eur} €"
    header += f"\n\n{record.description}"
    header += f"\n\n<b>ISBN:</b> {record.isbn}"
    header += f"\n\n<b>Номер строки:</b> {record.target_age}"
    header += f"\n\n{record.hashtag}"
    return header


def build_order_header(title: str, channel: Channel, record: Record, user_chat_id: int, user_handle: str | None, user_full_name: str | None) -> str:
    header = f"<b>{title}</b>"
    header += f"\n\n<b>🙂:</b> <a href='tg://user?id={str(user_chat_id)}'>{user_full_name}</a>"
    if user_handle:
        header += f" @{user_handle}"
    header += f"\n<b>{record.title}</b>"
    header += f"\n\n<b>ISBN:</b> {record.isbn}"
    header += f"\n<b>📚:</b> {channel.title} ({channel.worksheet_title})"
    if "РФ" in title:
        header += f"\n<b>💰:</b> {record.price_rub} ₽"
    else:
        header += f"\n<b>💰:</b> {record.price_eur} €"
    header += f"\n\n<b>⏰:</b> {datetime.now(timezone(timedelta(hours=3))).strftime('%d-%m-%Y %H:%M:%S')} МСК"
    return header


def build_item_log_header(record: Record, orders: ScalarResult[Order], rf: bool) -> str:

    header = f"<b>Список заказавших книгу \"{record.title}\"</b>\n"
    grouped_orders: dict[str, list[Order]] = {
        user_chat_id: list(user_orders)
        for user_chat_id, user_orders
        in groupby(list(orders), key=attrgetter("user_chat_id"))
    }
    for user_chat_id, user_orders in grouped_orders.items():
        handle: str | None = user_orders[0].user_handle
        print(user_orders[0])
        if handle:
            handle = f"@{handle}"
        else:
            handle = str(handle)
        num_rf = len(list(filter(lambda x: x.user_is_rf or print(x.user_is_rf), user_orders)))
        if num_rf>0:
            header += f"\n<a href='tg://user?id={str(user_chat_id)}'>{str(user_orders[0].user_full_name)}</a> - {handle} - {str(num_rf)} экз. РФ"
        num_eu = len(user_orders)-num_rf
        if num_eu>0:
            header += f"\n<a href='tg://user?id={str(user_chat_id)}'>{str(user_orders[0].user_full_name)}</a> - {handle} - {str(num_eu)} экз. EU"
        print(header)
    return header
