from typing import Any
import asyncio
import random
from datetime import datetime
from io import StringIO, BytesIO
from decimal import Decimal
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re
from redis import Redis
from aiogram import Bot, Dispatcher, F,types
from aiogram.exceptions import TelegramRetryAfter
from aiogram.enums import MessageOriginType
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, FSInputFile, BufferedInputFile, \
    LinkPreviewOptions, User
from aiogram.filters.command import Command
from aiogram.filters import CommandStart
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.media_group import MediaGroupBuilder, MediaType
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, update, delete, exists, func, ScalarResult
from sqlalchemy.ext.asyncio import AsyncSession
from middlewares import AccessMiddleware
from db_api import open_db_session, Channel, Group, Item, Order
from sheets_api import Record
from states import MenuState, Dialogue
from utils import config
from headers import build_channel_header, build_item_header, build_order_header, build_item_log_header
from keyboards import (
    MenuAction, EntryAction, ItemAction,
    build_channel_list_markup, build_channel_menu_markup, build_dialogue_markup,
    build_item_markup
)
from sheet_ip_for_user import add_new_order, remove_order, get_storka

bot: Bot = Bot(token=config["bot_token"])
storage: RedisStorage = RedisStorage.from_url("redis://localhost?db=" + str(config["redis_database_id"]))
dispatcher: Dispatcher = Dispatcher(storage=storage)
dispatcher.message.middleware(AccessMiddleware(access_ids=config["access_ids"]))


@dispatcher.message(CommandStart())
async def send_welcome(message: Message, state: FSMContext):
    await message.answer(text="Привет. Это Booktell Bot")


@dispatcher.message(Command("download"))
async def initialize_channel_list(message: Message, state: FSMContext):
    async with open_db_session() as session:
        channels: ScalarResult[Channel] = await session.scalars(select(Channel))
        answer = await message.answer("<b>Ваши каналы</b>", parse_mode="html",
                                      reply_markup=build_channel_list_markup(channels))
        await state.set_state(MenuState.Menu)
        await state.update_data({"current_entry_id": None, "menu_message_id": answer.message_id})
        # current_entry_id: an ID of a list entry user has navigated to or is manipulating
        # this must be set to None
        # when user finishes a respective interaction
        # menu_message_id: used in dialogues
        # and in restricting user from using two menus in parallel
        # to avoid potential crashes
        await session.commit()

async def generate_admins_keyboard():
    button_builder = InlineKeyboardBuilder()  # Изменил название переменной для ясности
    for admin_id in config["access_ids"]:
        user = await bot.get_chat(admin_id)
        button = InlineKeyboardButton(text=f"🗑 {user.username}", callback_data=f"remove_admin_{admin_id}")
        button_builder.add(button)  # Добавление кнопки в builder
    return button_builder.as_markup()  # Возвращаем объект InlineKeyboardMarkup


@dispatcher.message(Command("admin"))
async def admin_command(message: types.Message):
    if message.from_user.id in config["access_ids"]:
        keyboard = await generate_admins_keyboard()
        await message.answer(text="Администраторы:", reply_markup=keyboard)

@dispatcher.callback_query(lambda cq: cq.data.startswith('remove'))
async def remove_admin_callback(query: types.CallbackQuery):
    admin_id = int(query.data.split('_')[-1])
    if len(config["access_ids"]) > 1:
        if admin_id in config["access_ids"] :
            config["access_ids"].remove(admin_id)
            await query.message.edit_reply_markup(reply_markup = await generate_admins_keyboard())
            await query.answer("Администратор удален.")
        else:
            await query.answer("Этот пользователь не является администратором.")
    else:
            await query.answer("Это последний админ, пожалейте его")



@dispatcher.message(lambda message: message.text and message.text.startswith('/add_'))
async def add_admin_username(message: types.Message):
    # Проверяем, что сообщение начинается с /add_admin_
    userid = message.text.replace('/add_', '')  # Получаем username из сообщени
    try:
        int(userid)
        config["access_ids"].append(userid)
        await message.answer(f"Пользователь {userid} добавлен в список администраторов.")
    except ValueError:
        await message.answer("Пользователь с таким user id не найден.")


@dispatcher.callback_query(MenuAction.filter(F.action == "show_channel_list"))
async def show_channel_list(query: CallbackQuery, state: FSMContext, callback_data: MenuAction):
    if query.message.message_id == (await state.get_data())["menu_message_id"]:
        async with open_db_session() as session:
            channels: ScalarResult[Channel] = await session.scalars(select(Channel))
            await query.message.edit_text("<b>Каналы</b>", parse_mode="html",
                                          reply_markup=build_channel_list_markup(channels))
            await state.update_data({"current_entry_id": None})
    await query.answer()


@dispatcher.callback_query(EntryAction.filter(F.action == "show_channel_menu"))
async def show_channel_menu(query: CallbackQuery, state: FSMContext, callback_data: EntryAction):
    if query.message.message_id == (await state.get_data())["menu_message_id"]:
        async with open_db_session() as session:
            channel: Channel = await session.scalar(select(Channel).where(Channel.id == callback_data.entry_id))
            groups: ScalarResult[Group] = await session.scalars(select(Group).where(Group.channel_id == channel.id))
            await query.message.edit_text(build_channel_header(channel, groups), parse_mode="html",
                                          reply_markup=build_channel_menu_markup(channel))
            await state.update_data({"current_entry_id": channel.id})
    await query.answer()


@dispatcher.callback_query(MenuAction.filter(F.action == "delete_channel"))
async def delete_channel_show_list(query: CallbackQuery, state: FSMContext, callback_data: MenuAction):
    if query.message.message_id == (await state.get_data())["menu_message_id"]:
        async with open_db_session() as session:
            channel_id: str = (await state.get_data())["current_entry_id"]
            items: ScalarResult[Item] = await session.scalars(select(Item).where(Item.channel_id == channel_id))
            for item in items:
                await session.execute(delete(Order).where(Order.item_id == item.id))
                await session.delete(item)
            await session.flush()
            await session.execute(delete(Group).where(Group.channel_id == channel_id))
            await session.execute(delete(Channel).where(Channel.id == channel_id))
            channels: ScalarResult[Channel] = await session.scalars(select(Channel))
            await query.message.edit_text("<b>Каналы</b>", parse_mode="html",
                                          reply_markup=build_channel_list_markup(channels))
            await state.update_data({"current_entry_id": None})
            await session.commit()
    await query.answer()


@dispatcher.callback_query(MenuAction.filter(F.action == "ask_new_channel_message"))
async def ask_new_channel_message(query: CallbackQuery, state: FSMContext, callback_data: MenuAction):
    if query.message.message_id == (await state.get_data())["menu_message_id"]:
        async with open_db_session() as session:
            await query.message.edit_text("<b>Перешлите любое сообщения из канала, в который будут загружены книги</b>",
                                          parse_mode="html",
                                          reply_markup=build_dialogue_markup(Dialogue.NewChannelMessage.state))
            await state.set_state(Dialogue.NewChannelMessage)
    await query.answer()

@dispatcher.callback_query(MenuAction.filter(F.action == "publish_from_worksheet"))
async def publish_from_worksheet(query: CallbackQuery, state: FSMContext, callback_data: MenuAction):
    await query.message.edit_text(text="<b>С какой строки начнём заполнение?</b>", parse_mode="html")
    await state.set_state(Dialogue.row_number)  

@dispatcher.message(Dialogue.row_number)
async def get_row_number(message: Message, state: FSMContext):
    async with open_db_session() as session:
        channel: Channel = await session.scalar(
            select(Channel).where(Channel.id == (await state.get_data())["current_entry_id"]))
        groups: ScalarResult[Group] = await session.scalars(select(Group).where(Group.channel_id == channel.id))
        records: list[Record] = await Record.from_gspread(channel.worksheet_title, message.text)
        x = await message.answer("1")
        await x.edit_text(text="<b>Идет заполнение канала...</b>", parse_mode="html")
        for record in records:
            try:
                media_group = MediaGroupBuilder()
                for picture in record.pictures:
                    media_group.add_photo(picture)
                media: list[MediaType] = media_group.build()
                if media:
                    await asyncio.sleep(1)
                    while True:
                        try:
                            await bot.send_media_group(chat_id=channel.chat_id, media=media)
                            break
                        except TelegramRetryAfter as e:
                            await asyncio.sleep(e.retry_after)
                    await asyncio.sleep(1 * len(media))
                await asyncio.sleep(1)
                while True:
                    try:
                        record.target_age = get_storka(record.isbn , channel.worksheet_title)
                        await bot.send_message(chat_id=channel.chat_id, text=build_item_header(record),
                                                parse_mode="html", reply_markup=build_item_markup(record.isbn))
                        break
                    except TelegramRetryAfter as e:
                        await asyncio.sleep(e.retry_after)
                await asyncio.sleep(1)
                log_message: Message
                while True:
                    try:
                        log_message = await bot.send_message(chat_id=channel.chat_id,
                                                                text=f"<b>Список заказавших книгу \"{record.title}\"</b>",
                                                                parse_mode="html")
                        break
                    except TelegramRetryAfter as e:
                        await asyncio.sleep(e.retry_after)
                item: Item = Item(channel_id=channel.id, log_message_id=log_message.message_id, isbn=record.isbn)
                session.add(item)
                await session.flush()
            except Exception as e:
                await message.answer(f"<b>Ошибка на {record.isbn}!</b>\n\n<pre>\n{str(e)}\n</pre>",
                                            parse_mode="html")
        # await message.edit_text(build_channel_header(channel, groups), parse_mode="html",
        #                                 reply_markup=build_channel_menu_markup(channel))
        await session.commit()
        await x.edit_text(text="<b>Канал заполнен.</b>", parse_mode="html")

# @dispatcher.callback_query(MenuAction.filter(F.action == "publish_from_worksheet"))
# async def publish_from_worksheet(query: CallbackQuery, state: FSMContext, callback_data: MenuAction):
#     # if query.message.message_id == (await state.get_data())["menu_message_id"]:
#     async with open_db_session() as session:
#         channel: Channel = await session.scalar(select(Channel).where(Channel.id == (await state.get_data())["current_entry_id"]))
#         groups: ScalarResult[Group] = await session.scalars(select(Group).where(Group.channel_id == channel.id))
#         records: list[Record] = await Record.from_gspread(channel.worksheet_title)

#         await query.answer(text="<b>Идет заполнение канала...</b>", parse_mode="html")
#         for record in records:
#             try:
#                 media_group = MediaGroupBuilder()
#                 for picture in record.pictures:
#                     media_group.add_photo(picture)
#                 media: list[MediaType] = media_group.build()
#                 if media:
#                     await asyncio.sleep(1)
#                     while True:
#                         try:
#                             await bot.send_media_group(chat_id=channel.chat_id, media=media)
#                             break
#                         except TelegramRetryAfter as e:
#                             await asyncio.sleep(e.retry_after)
#                     await asyncio.sleep(3*len(media))
#                 await asyncio.sleep(1)
#                 while True:
#                     try:
#                         await bot.send_message(chat_id=channel.chat_id, text=build_item_header(record), parse_mode="html", reply_markup=build_item_markup(record.isbn))
#                         break
#                     except TelegramRetryAfter as e:
#                         await asyncio.sleep(e.retry_after)
#                 await asyncio.sleep(1)
#                 log_message: Message
#                 while True:
#                     try:
#                         log_message = await bot.send_message(chat_id=channel.chat_id, text=f"<b>Список заказавших книгу \"{record.title}\"</b>", parse_mode="html")
#                         break
#                     except TelegramRetryAfter as e:
#                         await asyncio.sleep(e.retry_after)
#                 item: Item = Item(channel_id=channel.id, log_message_id=log_message.message_id, isbn=record.isbn)
#                 session.add(item)
#                 await session.flush()
#             except Exception as e:
#                 await query.message.answer(f"<b>Ошибка на {record.isbn}!</b>\n\n<pre>\n{str(e)}\n</pre>", parse_mode="html")
#         # await query.message.edit_text(build_channel_header(channel, groups), parse_mode="html", reply_markup=build_channel_menu_markup(channel))
#         # await query.answer(build_channel_header(channel, groups), parse_mode="html", reply_markup=build_channel_menu_markup(channel))
#         await session.commit()
#         print("commit done")


@dispatcher.callback_query(ItemAction.filter())
async def do_order_action(query: CallbackQuery, state: FSMContext, callback_data: ItemAction):
    async with open_db_session() as session:
        channel: Channel = await session.scalar(select(Channel).where(Channel.chat_id == query.message.chat.id))
        groups: ScalarResult[Group] = await session.scalars(select(Group).where(Group.channel_id == channel.id))
        records: list[Record] = await Record.from_gspread(channel.worksheet_title)
        subject_record: Record
        item: Item
        user_full_name: str | None = ""
        title: str
        pop_up: str

        for record in records:
            if record.isbn == callback_data.isbn:
                subject_record = record
                break
        else:
            raise Exception("Record not found")
        item = await session.scalar(select(Item)
                                    .where(
                                        Item.isbn == subject_record.isbn
                                                       , Item.channel_id == channel.id
                                                       )
        )
        if item:
            
            if query.from_user.first_name:
                user_full_name = query.from_user.first_name
            if query.from_user.last_name:
                user_full_name += " " + query.from_user.last_name
            if not user_full_name:
                user_full_name = None
    
            match callback_data.action:
                case "orderRF":
                    rf = True
                    cancel = False
                    title = "🎊 Новый заказ РФ! 🎊"  # РФ - не менять
                    pop_up = f"Вы заказали книгу \"{subject_record.title}\""
                    order: Order = Order(item_id=item.id, user_chat_id=query.from_user.id, user_full_name=user_full_name,
                                         user_handle=query.from_user.username, user_is_rf = True)
                    session.add(order)
                case "orderEU":
                    rf = False
                    cancel = False
                    title = "🎊 Новый заказ EU! 🎊"
                    pop_up = f"Вы заказали книгу \"{subject_record.title}\""
                    order: Order = Order(item_id=item.id, user_chat_id=query.from_user.id, user_full_name=user_full_name,
                                         user_handle=query.from_user.username, user_is_rf = False)
                    session.add(order)
                    
                case "cancel_orderRF":
                    cancel = True
                    rf = True
                    title = "🫠 Отмена заказа РФ! 🫠"  # РФ - не менять
                    pop_up = f"Вы отменили заказ на книгу \"{subject_record.title}\""
                    order: Order = await session.scalar(
                        select(Order).where(Order.item_id == item.id, Order.user_chat_id == query.from_user.id, Order.user_is_rf == True).order_by(
                            Order.created_at.desc()))
                    try:
                        await session.delete(order)
                    except:
                        await query.answer(text="У Вас нет заказов!")
                case "cancel_orderEU":
                    title = "🫠 Отмена заказа EU! 🫠"
                    rf = False
                    cancel = True
                    pop_up = f"Вы отменили заказ на книгу \"{subject_record.title}\""
                    order: Order = await session.scalar(
                        select(Order).where(Order.item_id == item.id, Order.user_chat_id == query.from_user.id, Order.user_is_rf==False).order_by(
                            Order.created_at.desc()))
                    try:
                        await session.delete(order)
                    except:
                        await query.answer(text="У Вас нет заказов!")
            await session.flush()
    
            for group in groups:
    
                await bot.send_message(chat_id=group.chat_id,
                                       text=build_order_header(title, channel, subject_record, query.from_user.id,
                                                               query.from_user.username, user_full_name), parse_mode="html",
                                       link_preview_options=LinkPreviewOptions(is_disabled=True))
            if rf and not cancel:
                add_new_order(record.isbn, channel.worksheet_title, "РФ", query.from_user.id, query.from_user.username)
            if not rf and not cancel:
                add_new_order(record.isbn, channel.worksheet_title, "ЕС", query.from_user.id, query.from_user.username)
            if cancel:
                remove_order(query.from_user.id, record.isbn)
    
            orders: ScalarResult[Order] = await session.scalars(
                select(Order).where(Order.item_id == item.id).order_by(Order.user_chat_id.desc()))
            await bot.edit_message_text(text=f"{build_item_log_header(subject_record, orders, rf)}", chat_id=channel.chat_id, message_id=item.log_message_id, parse_mode="html")
            
            
            await query.answer(text=pop_up)
            await session.commit()
        else:
            print("item is none")


@dispatcher.callback_query(MenuAction.filter(F.action == "end_dialogue"))
async def end_dialogue(query: CallbackQuery, state: FSMContext, callback_data: MenuAction):
    if query.message.message_id == (await state.get_data())["menu_message_id"]:
        async with open_db_session() as session:
            current_entry_id: int = (await state.get_data())["current_entry_id"]
            text: str
            markup: InlineKeyboardMarkup
            match (await state.get_state()).split(":")[1]:
                case "NewChannelMessage":
                    channels: ScalarResult[Channel] = await session.scalars(select(Channel))
                    text = "<b>Каналы</b>"
                    markup = build_channel_list_markup(channels)
                case "GroupMessage":
                    channel: Channel = await session.scalar(select(Channel).where(Channel.id == current_entry_id))
                    groups: ScalarResult[Group] = await session.scalars(
                        select(Group).where(Group.channel_id == channel.id))
                    text = build_channel_header(channel, groups)
                    markup = build_channel_menu_markup(channel)
            await query.message.edit_text(text, parse_mode="html", reply_markup=markup)
            await state.set_state(MenuState.Menu)
    await query.answer()


@dispatcher.message(Dialogue.NewChannelMessage)
async def set_new_channel_chat_id_ask_sheet_title(message: Message, state: FSMContext):
    await message.delete()
    if message.forward_origin is not None:
        if message.forward_origin.type == MessageOriginType.CHANNEL:
            async with open_db_session() as session:
                if not await session.scalar(select(Channel).where(Channel.chat_id == message.forward_origin.chat.id)):
                    channel: Channel = Channel(title=message.forward_origin.chat.title,
                                               chat_id=message.forward_origin.chat.id)
                    session.add(channel)
                    await session.flush()
                    await bot.edit_message_text(
                        text=build_channel_header(channel, []) + "<b>\n\nВведите название листа Google-таблицы</b>",
                        chat_id=message.from_user.id, message_id=(await state.get_data())["menu_message_id"],
                        parse_mode="html", reply_markup=build_dialogue_markup(Dialogue.WorksheetTitle.state))
                    await state.update_data({"current_entry_id": channel.id})
                    await state.set_state(Dialogue.WorksheetTitle)
                    await session.commit()


@dispatcher.message(Dialogue.WorksheetTitle)
async def set_channel_sheet_title_ask_group_message(message: Message, state: FSMContext):
    await message.delete()
    if message.text is not None:
        async with open_db_session() as session:
            channel: Channel = await session.scalar(
                select(Channel).where(Channel.id == (await state.get_data())["current_entry_id"]))
            channel.worksheet_title = message.text
            await session.flush()
            await bot.edit_message_text(text=build_channel_header(channel,
                                                                  []) + "\n\n<b>Перешлите любое сообщение, отправленное от лица группы, в которую будут отправляться заказы</b>",
                                        chat_id=message.from_user.id,
                                        message_id=(await state.get_data())["menu_message_id"], parse_mode="html",
                                        reply_markup=build_dialogue_markup(Dialogue.GroupMessage.state))
            await state.set_state(Dialogue.GroupMessage)
            await session.commit()


@dispatcher.message(Dialogue.GroupMessage)
async def add_channel_group(message: Message, state: FSMContext):
    await message.delete()
    if message.forward_origin is not None:
        if message.forward_origin.type == MessageOriginType.CHAT:
            async with open_db_session() as session:
                channel: Channel = await session.scalar(
                    select(Channel).where(Channel.id == (await state.get_data())["current_entry_id"]))
                group: Group = Group(channel_id=channel.id, title=message.forward_origin.sender_chat.title,
                                     chat_id=message.forward_origin.sender_chat.id)
                session.add(group)
                await session.flush()
                groups: ScalarResult[Group] = await session.scalars(select(Group).where(Group.channel_id == channel.id))
                await bot.edit_message_text(text=build_channel_header(channel,
                                                                      groups) + "\n\n<b>Перешлите любое сообщение, отправленное от лица группы, в которую будут отправляться заказы</b>",
                                            chat_id=message.from_user.id,
                                            message_id=(await state.get_data())["menu_message_id"], parse_mode="html",
                                            reply_markup=build_dialogue_markup(Dialogue.GroupMessage.state))
                await session.commit()
