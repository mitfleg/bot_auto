import traceback
from aiogram import types
from bot import dp, bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
from handlers.account import sendError
from handlers.common import getConfig, check_rights
from ..db import DataBase

main_conf = getConfig('auto')
price_phone = main_conf['price_phone']
price_city = main_conf['price_city']
price_area = main_conf['price_area']


@dp.callback_query_handler(lambda c: c.data.split('_')[0] == 'get')
async def get(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    try:
        async with DataBase() as db:
            query = await db.read('users', where="user_id={}".format(chat_id))
            balance = query[0]["balance"]
            type_get = call.data.split('_')[1]
            id_avtocod = call.data.split('_')[2]
            user_rights_bool = await check_rights(chat_id)
            if user_rights_bool == 1 or user_rights_bool == 2 or user_rights_bool == 0:
                query = await db.read('history', where="id_avtocod='{}'".format(id_avtocod))
                info_owner = json.loads(
                    query[0]['info_owner'].replace("'", '"'))

                async def __no_money(price):
                    msg = "❌ На вашем счету недостаточно средств!\n"
                    msg += "- - - - - - - - - - - - - -\n"
                    msg += f"<b>Ваш баланс:</b> <code>{balance}₽</code>"
                    inline_btn_1 = InlineKeyboardButton(
                        f"💳 Пополнить баланс на сумму {price-balance} ₽", callback_data="payment_" + str(price - balance))
                    menu = InlineKeyboardButton("📰 Меню", callback_data="menu")
                    inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1).add(menu)
                    await call.message.answer(msg, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)

                if type_get == 'area':
                    if balance >= price_area:
                        if price_area > 0:
                            await db.decrement("users", "balance", price_area, where=f"user_id={chat_id}")
                            await db.insert('operations', ['user_id', 'transaction_type', 'transaction'], [chat_id, 'writedowns', f'{price_area}₽ - Получение района проживания'])
                        msg = f"Регион: <code>" + \
                            info_owner['area_reg']+"</code>"
                        await call.message.answer(msg, parse_mode=types.ParseMode.HTML)
                    else:
                        await __no_money(price_area)
                if type_get == 'city':
                    if balance >= price_city:
                        if price_city > 0:
                            await db.decrement("users", "balance", price_city, where=f"user_id={chat_id}")
                            await db.insert('operations', ['user_id', 'transaction_type', 'transaction'], [chat_id, 'writedowns', f'{price_city}₽ - Получение города проживания'])
                        msg = f"Город: <code>"+info_owner['city_reg']+"</code>"
                        await call.message.answer(msg, parse_mode=types.ParseMode.HTML)
                    else:
                        await __no_money(price_city)
                if type_get == 'phone':
                    if balance >= price_phone:
                        phone_number = info_owner['owner_phone'].split(', ')
                        msg = f"<b>Возможные</b> номера телефона:\n"
                        for item in phone_number:
                            msg += '<code>'+item+'</code>\n'
                        if price_phone > 0:
                            await db.decrement("users", "balance", price_phone, where=f"user_id={chat_id}")
                            await db.insert('operations', ['user_id', 'transaction_type', 'transaction'], [chat_id, 'writedowns', f'{price_phone}₽ - Получение номера телефона'])
                        await call.message.answer(msg, parse_mode=types.ParseMode.HTML)
                    else:
                        await __no_money(price_phone)
            else:
                msg = f"У вас нет прав для просмотра этой информации"
                await call.message.answer(msg, parse_mode=types.ParseMode.HTML)
    except Exception as exc:
        await sendError(call.message)
