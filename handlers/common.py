from datetime import datetime
import json
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from handlers.db import DataBase


async def getBalance(user_id):
    async with DataBase() as db:
        balance = await db.read("users", ["balance"], where=f"user_id={user_id}")
        return balance[0]["balance"]


def enough_funds(balance, price_per_request):
    return balance >= price_per_request


def insufficient_funds_message(balance, price_per_request):
    msg = "❌ Недостаточно средств!\n"
    msg += "- - - - - - - - - - - - - -\n"
    msg += f"<b>Баланс:</b> <code>{balance:.2f}₽</code>\n"
    msg += f"<b>Стоимость запроса:</b> <code>{price_per_request:.2f}₽</code>"
    return msg


def getConfig(key):
    with open("./config.json", "r", encoding="utf8") as f:
        return json.load(f)[f"{key}"]


ADMIN_ID = getConfig('ADMIN')


async def check_rights(user_id):
    async with DataBase() as db:
        query = await db.read('users', ['user_rights'], where="user_id={}".format(user_id))
        return query[0]['user_rights']


async def main_menu_all(message):
    user_id = message.chat.id
    inline_btn_1 = InlineKeyboardButton('⚙️ Аккаунт', callback_data='account')
    inline_btn_2 = InlineKeyboardButton('🆘 Помощь', callback_data='help')
    inline_kb1 = InlineKeyboardMarkup().row(inline_btn_1, inline_btn_2)
    msg = '🤔 <b>Вы можете прислать боту запросы в следующем формате:</b>\n\n '
    msg += '🚗 <b>Поиск по технике</b> \n'
    msg += '├ <code>О810РР123</code> - Поиск авто по <b>РФ</b> \n'
    msg += '├ <code>XTA21150053965897</code> - Поиск по <b>VIN</b> \n'
    msg += '└ <code>2222НН77</code> - Поиск мото по <b>РФ</b> \n\n'

    if await check_rights(user_id) == 1:
        admin = InlineKeyboardButton(
            '🛠 Администратор', callback_data='admin')
        help_btn = InlineKeyboardButton(
            '🆘 Войти в чат', callback_data='chat_help')
        inline_kb1.row(admin, help_btn)
        msg += '📱 Поиск по номеру телефона\n'
        msg += '└ Формат номера телефона <code>79850264551</code>\n\n'


    response = {
        "msg": msg,
        "btns": inline_kb1,
    }
    return response


def plural_days(n):
    days = ['день', 'дня', 'дней']

    if n % 10 == 1 and n % 100 != 11:
        p = 0
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        p = 1
    else:
        p = 2
    return str(n) + ' ' + days[p]


def get_month(n):
    month = [
        'января',
        'февраля',
        'марта',
        'апреля',
        'мая',
        'июня',
        'июля',
        'августа',
        'сентября',
        'октября',
        'ноября',
        'декабря',
    ]
    return month[n]


def format_datetime(date_string: str, short=False) -> str:
    date = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
    date = date.replace(hour=(date.hour+3) % 24)
    day = date.strftime('%d')
    month = get_month(int(date.strftime('%m'))-1)
    year = date.strftime('%Y')
    time = date.strftime('%H:%M')
    if short:
        return f"{day} {month} {year}"
    return f"{day} {month} {year} {time}"


def get_grouped_items(history):
    grouped_items = {}
    for item in history:
        date_created = item['date_created'].strftime('%d.%m.%Y')
        if date_created in grouped_items:
            grouped_items[date_created].append(item)
        else:
            grouped_items[date_created] = [item]
    return grouped_items


def format_history_item(item, operation=False):
    time = item['date_created'].strftime('%H:%M')
    if operation:
        request = item['transaction']
        if request[0] == '-':
            request = request[1:]
    else:
        request = f"<code>{item['request'].upper()}</code>"
    return f'{time} - {request}'
