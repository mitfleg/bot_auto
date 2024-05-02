from aiogram import types
from bot import dp, bot
from .common import main_menu_all
from handlers.db import DataBase


@dp.message_handler(text='Меню ℹ️')
async def menu(message: types.Message):
    await main_menu_all(message)


@dp.message_handler(commands='menu')
async def menu(message: types.Message):
    async with DataBase() as db:
        query = await db.read('users', where="user_id={}".format(message.chat.id))
        auth = query[0]
    if auth:
        result = await main_menu_all(message)
        try:
            await bot.edit_message_text(result['msg'], message.chat.id, message.message_id, reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)
        except:
            await message.answer(result['msg'], reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)
    else:
        await message.answer('🤔 <b>Вы не зарегистрированы. Введите команду /start и повторите регистрацию</b>', parse_mode=types.ParseMode.HTML)
