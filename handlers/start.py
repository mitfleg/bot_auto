from aiogram import types
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from bot import dp, bot
from aiogram.dispatcher.filters.builtin import CommandStart
from handlers.db import DataBase
from .common import main_menu_all, ADMIN_ID


@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    msg = '<b>Добро пожаловать в поисковую систему!</b>\n\n'
    msg += 'Сервис является <b>инструментом</b> по поиску информации об автомобилях и использует для поиска открытые и общедоступные банки данных. '
    msg += 'Сервис работает в режиме реального времени и формирует отчёт <b>«на ходу»</b>, то есть <b>без сохранения</b> всей полученной информации.'
    await message.answer(msg, parse_mode=types.ParseMode.HTML)
    phone = KeyboardButton(
        text='Подтвердить номер телефона ✅', request_contact=True)
    greet_kb = ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True)
    greet_kb.add(phone)
    await message.answer('Вам необходимо <b>подтвердить номер телефона</b> для того, чтобы завершить <b>идентификацию.</b>\n\n<b>Для этого нажмите кнопку ниже.</b>', reply_markup=greet_kb, parse_mode=types.ParseMode.HTML)


@dp.message_handler(content_types=['contact'])
async def read_contact_phone(message: types.Message):
    message_id = message.message_id
    phone_usm = message.contact.phone_number
    if message.chat.username == None:
        msg = '🤔 <b>Имя пользователя не найдено.</b>\n\n '
        msg += 'Создайте его, следуя по пути \n '
        msg += '<code>Настройки</code>><code>Изменить</code>><code>Имя пользователя</code>><code>"Введите имя"</code>><code>Готово</code>\n '
        msg += 'После введите команду /start\n '
        await message.answer(msg, parse_mode=types.ParseMode.HTML)
        return
    async with DataBase() as db:
        await db.create('users', ['user_name', 'user_id', 'user_phone'], [message.chat.username, message.chat.id, phone_usm])
    await message.delete()
    try:
        await bot.delete_message(message.chat.id, message_id-1)
        await bot.delete_message(message.chat.id, message_id-2)
    except:
        pass
    greet_kb = ReplyKeyboardRemove()
    await message.answer('✅ <b>Номер телефона успешно подтвержден!</b>', reply_markup=greet_kb, parse_mode=types.ParseMode.HTML)
    await message.answer('👋 <b>Приветствую!</b>', parse_mode=types.ParseMode.HTML)
    try:
        await bot.send_message(ADMIN_ID, f'Регистрация пользователя: <code>{message.chat.username}</code>\nНомер телефона: <code>{phone_usm}</code>', parse_mode=types.ParseMode.HTML)
    except:
        pass

    result = await main_menu_all(message)
    try:
        await bot.edit_message_text(result['msg'], message.chat.id, message_id, reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)
    except:
        await message.answer(result['msg'], reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)
