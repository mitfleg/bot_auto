import traceback
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import dp, bot
from .common import getConfig
from handlers.account import sendError


@dp.callback_query_handler(text='help')
async def help(call: types.CallbackQuery):
    message_id = call.message.message_id
    try:
        msg = '<b>🔎 Система для поиска информации по открытым источникам информации.</b>\n'
        inline_btn_1 = InlineKeyboardButton('❓ Вопросы и ответы', callback_data='faq')
        inline_btn_2 = InlineKeyboardButton('💬 Задать вопрос', callback_data='send_question')
        back = InlineKeyboardButton('🔙 Назад', callback_data='back|mainmenu')
        inline_kb1 = InlineKeyboardMarkup().row(inline_btn_1, inline_btn_2).add(back)
        await bot.edit_message_text(msg, call.message.chat.id, message_id, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text='faq')
async def faq(call: types.CallbackQuery):
    message_id = call.message.message_id
    try:
        about = getConfig('about_page')
        msg = 'ℹ️ <b>Полезная информация</b>\n\n'
        for i in about:
            msg += f"<b>{i['descr']}</b>:\n{i['link']}\n\n"
        inline_btn_1 = InlineKeyboardButton('💬 Задать вопрос', callback_data='send_question')
        back = InlineKeyboardButton('🔙 Назад', callback_data='back|help')
        inline_kb1 = InlineKeyboardMarkup().row(inline_btn_1).add(back)
        await bot.edit_message_text(msg, call.message.chat.id, message_id, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML, disable_web_page_preview=True)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text='send_question')
async def send_question(call: types.CallbackQuery):
    message_id = call.message.message_id
    try:
        msg = '🛠 <b>Сервис чата в разработке</b>\n\n'
        msg += 'В ближайщее время он будет готов\n'
        msg += 'На данный момент, вы можете отправить сообщение пользователю @mitfleg\n'
        menu = InlineKeyboardButton('🔙 Назад', callback_data='back|help')
        inline_kb1 = InlineKeyboardMarkup().add(menu)
        await bot.edit_message_text(msg, call.message.chat.id, message_id, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
    except Exception as exc:
        await sendError(call.message)
