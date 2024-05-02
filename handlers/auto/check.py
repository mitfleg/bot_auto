from aiogram import types
import base64
from bot import dp, bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
from aiogram.dispatcher.filters import Filter
import re
import datetime
from datetime import date
from handlers.account import sendError
from .get_full_info import main_mini
from aiogram.types.web_app_info import WebAppInfo
from ..db import DataBase
from ..common import check_rights, getConfig

main_conf = getConfig('auto')
price_otchet = main_conf['price_otchet']
price_phone = main_conf['price_phone']
price_city = main_conf['price_city']
price_area = main_conf['price_area']


class IsNumber(Filter):
    async def check(self, message: types.Message):
        gos_number = [
            r"^(?i)[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}",
            r"^(?i)[АВЕКМНОРСТУХ]{2}\d{3}\d{2,3}",
            r"^(?i)[АВЕКМНОРСТУХ]{2}\d{4}\d{2,3}",
            r"^(?i)\d{4}[АВЕКМНОРСТУХ]{2}\d{2,3}",
            r"^(?i)[АВЕКМНОРСТУХ]{2}\d{3}[АВЕКМНОРСТУХ]\d{2,3}",
            r"^(?i)Т[АВЕКМНОРСТУХ]{2}\d{3}\d{2,3}",
            r"^(?i)[АВЕКМНОРСТУХ]\d{5,6}",
            r"^(?i)[A-HJ-NPR-Za-hj-npr-z\d]{8}[\dX][A-HJ-NPR-Za-hj-npr-z\d]{2}\d{6}$",
            r"^(?i)[A-HJ-NPR-Z0-9]{17}",
        ]
        regexps_compiled = [re.compile(r) for r in gos_number]
        for regex in regexps_compiled:
            if re.findall(regex, message.text):
                return True
        return False


def years(n):
    days = ["год", "года", "лет"]

    if n % 10 == 1 and n % 100 != 11:
        p = 0
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        p = 1
    else:
        p = 2
    return str(n) + " " + days[p]


async def yes_osago(all_info, subscribe, number, user_id):
    result = all_info['result']['content']['content']
    osago = result['insurance']['osago']
    orgosago = osago['items'][0]['insurer']['name']
    area_reg = 'найдено' if 'region' in result['additional_info']['vehicle']['owner']['geo'] else 'не найдено'
    area_reg_db = result['additional_info']['vehicle']['owner']['geo'][
        'region'] if 'region' in result['additional_info']['vehicle']['owner']['geo'] else ''

    city_reg = 'найдено' if 'city' in result['additional_info']['vehicle']['owner']['geo'] else 'не найдено'
    city_reg_db = result['additional_info']['vehicle']['owner']['geo'][
        'city'] if 'city' in result['additional_info']['vehicle']['owner']['geo'] else ''

    phone = [
        r"^((\+7|7|8)+([0-9]){10})$",
        r"^(\+)?((\d{2,3}) ?\d|\d)(([ -]?\d)|( ?(\d{2,3}) ?)){5,12}\d$",
    ]

    regexps_compiled = [re.compile(r) for r in phone]

    if 'phone_number' in result['additional_info']['vehicle']['owner']:
        for regex in regexps_compiled:
            if re.findall(regex, result['additional_info']['vehicle']['owner']['phone_number']):
                owner_phone = 'найдено'
                owner_phone_db = result['additional_info']['vehicle']['owner']['phone_number']

    elif int(result['registration_actions']['count']) > 0:
        phone_array = []
        owner_phone = 'не найдено'
        for item in result['registration_actions']['items']:
            __phone = item['owner']['phone_number'] if 'phone_number' in item['owner'] else None
            if __phone != None:
                for regex in regexps_compiled:
                    if re.findall(regex, __phone):
                        if __phone not in phone_array:
                            phone_array.append(__phone)
                        owner_phone = 'найдено'
            owner_phone_db = ''
        owner_phone_db = ', '.join(phone_array)
    else:
        owner_phone = 'не найдено'
        owner_phone_db = ''

    info_owner = {
        'area_reg': area_reg_db,
        'city_reg': city_reg_db,
        'owner_phone': owner_phone_db
    }

    if subscribe:
        vin = result['identifiers']['vehicle']['vin'] if 'vin' in result['identifiers']['vehicle'] else 'нет данных'
        reg = result['identifiers']['vehicle']['reg_num'] if 'reg_num' in result['identifiers']['vehicle'] else 'нет данных'
        marka = osago['items'][0]['vehicle']['model']['name'] if 'name' in osago['items'][0]['vehicle']['model'] else result[
            'tech_data']['brand']['name']['original'] if 'original' in result['tech_data']['brand']['name'] else 'нет данных'
        owner = osago['items'][0]['owner']['name'] if 'name' in osago['items'][0]['owner'] else osago[
            'items'][0]['insurant']['name'] if 'name' in osago['items'][0]['insurant'] else 'нет данных'
        burthday_old = osago['items'][0]['owner']['dob'] if 'dob' in osago['items'][0]['owner'] else osago[
            'items'][0]['insurant']['dob'] if 'dob' in osago['items'][0]['insurant'] else ''
        try:
            burthday = datetime.datetime.strptime(burthday_old, "%Y-%m-%d")
            birthday_str = ""
            if burthday_old:
                birthday_str = burthday_old.split(
                    '-')[2]+'.'+burthday_old.split('-')[1]+'.'+burthday_old.split('-')[0]
                birthday_str = f"├ <b>Дата рождения:</b> <code>{birthday_str}</code>\n"
            today = date.today()
            age = (
                today.year
                - burthday.year
                - ((today.month, today.day) < (burthday.month, burthday.day))
            )
            age = str(years(age))
            age = f"├ <b>Возраст:</b> <code>{age}</code>\n"
        except:
            birthday_str = ""
            age = ""
        kbm = osago['items'][0]['contract']['kbm'] if 'kbm' in osago['items'][0]['contract'] else 'нет данных'
        strahsum = osago['items'][0]['contract']['amount']['value'] if 'value' in osago['items'][0]['contract']['amount'] else 'нет данных'
        status = osago['items'][0]['policy']['status'] if 'status' in osago['items'][0]['policy'] else 'нет данных'
        power = osago['items'][0]['vehicle']['engine']['power']['hp'] if 'hp' in osago['items'][0]['vehicle']['engine'][
            'power'] else result['tech_data']['engine']['power']['hp'] if 'hp' in result['tech_data']['engine']['power'] else 'нет данных'
        nomer = osago['items'][0]['number'] if 'number' in osago['items'][0] else 'нет данных'

        owner_count = result['ownership']['history']['count'] if 'count' in result['ownership']['history'] else 'нет данных'
        dtp_count = result['accidents']['history']['count'] if 'count' in result['accidents']['history'] else 'нет данных'
        mileages_count = result['mileages']['count'] if 'count' in result['mileages'] else 'нет данных'

    else:
        vin = 'найдено' if 'vin' in result['identifiers']['vehicle'] else 'не найдено'
        reg = 'найдено' if 'reg_num' in result['identifiers']['vehicle'] else 'не найдено'
        marka = 'найдено' if 'name' in osago['items'][0]['vehicle']['model'] else 'не найдено'
        owner = 'найдено' if 'name' in osago['items'][0]['owner'] else 'не найдено'
        birthday_str = ''
        age = ''
        kbm = 'найдено' if 'kbm' in osago['items'][0]['contract'] else 'не найдено'
        strahsum = 'найдено' if 'value' in osago['items'][0]['contract']['amount'] else 'не найдено'
        status = 'найдено' if 'status' in osago['items'][0]['policy'] else 'не найдено'
        power = 'найдено' if 'hp' in osago['items'][0]['vehicle']['engine']['power'] else 'не найдено'
        nomer = 'найдено' if 'number' in osago['items'][0] else 'не найдено'

        owner_count = 'найдено' if 'count' in result['ownership']['history'] else 'не найдено'
        dtp_count = 'найдено' if 'count' in result['accidents']['history'] else 'не найдено'
        mileages_count = 'найдено' if 'count' in result['mileages'] else 'не найдено'

    type_check = all_info['result']['content']['query']['type']
    msg = "#️⃣\n"
    if type_check == "VIN":
        msg += f"└ <b>VIN:</b> <code>{number}</code>\n\n"
    else:
        msg += f"└ <b>Номер:</b> <code>{number}</code>\n\n"

    msg += f"📋 <b>{orgosago}</b>\n"
    msg += f"├ <b>VIN:</b> <code>{vin}</code>\n"
    msg += f"├ <b>Г/н:</b> <code>{reg}</code>\n"
    msg += f"├ <b>Модель:</b> <code>{marka}</code>\n"
    msg += f"├ <b>Владелец:</b> <code>{owner}</code>\n"
    msg += birthday_str
    msg += age
    msg += f"├ <b>КБМ:</b> <code>{kbm}</code>\n"
    msg += f"├ <b>Страховая премия:</b> <code>{strahsum}</code>\n"
    msg += f"├ <b>Статус:</b> <code>{status}</code>\n"
    msg += f"├ <b>Мощность:</b> <code>{power}</code>\n"
    msg += f"└ <b>Полис:</b> <code>{nomer}</code>\n\n"

    msg += f"📃 <b>Владельцы</b>\n"
    if subscribe:
        msg += f"└ <b>Колличество:</b> <code>{owner_count}</code>\n\n"
    else:
        msg += f"└ <b>Колличество:</b> <code>Закрыто</code>\n\n"

    msg += f"🚔 <b>ДТП</b>\n"
    if subscribe:
        msg += f"└ <b>Колличество:</b> <code>{dtp_count}</code>\n\n"
    else:
        msg += f"└ <b>Колличество:</b> <code>Закрыто</code>\n\n"

    msg += f"🗺 <b>История пробега</b>\n"
    if subscribe:
        msg += f"└ <b>Колличество:</b> <code>{mileages_count}</code>\n\n"
    else:
        msg += f"└ <b>Колличество:</b> <code>Закрыто</code>\n\n"

    user_rights_bool = await check_rights(user_id)
    if user_rights_bool == 1 or user_rights_bool == 2 or user_rights_bool == 0:
        if info_owner['area_reg'] != '' or info_owner['city_reg'] != '' or info_owner['owner_phone'] != '':
            msg += f"👨‍🦰 <b>Данные о владельце</b>\n"
            if info_owner['area_reg'] != '':
                msg += f"├ <b>Район регистрации:</b> <code>{area_reg}</code>\n"
            if info_owner['city_reg'] != '':
                msg += f"├ <b>Город регистрации:</b> <code>{city_reg}</code>\n"
            if info_owner['owner_phone'] != '':
                msg += f"└ <b>Номер телефона:</b> <code>{owner_phone}</code> (50/50)\n\n"

    if not subscribe:
        msg += "❓Для просмотра информации под статусом <code>Закрыто</code> необходимо <b>Оформить подписку</b> или купить <b>Технический отчет</b>"

    photo = []
    if subscribe:
        if int(result["images"]['photos']['count']) > 0:
            count = 0
            for item in result["images"]['photos']['items']:
                if count == 5:
                    break
                photo.append(item["uri"])
                count += 1

    response = {"msg": msg, "photo": photo, "subscribe": subscribe,
                'uuid': all_info['result']['uuid'], 'info_owner': info_owner}
    return response


async def no_osago(all_info, subscribe, number, user_id):
    result = all_info['result']['content']['content']
    area_reg = 'найдено' if 'region' in result['additional_info']['vehicle']['owner']['geo'] else 'не найдено'
    area_reg_db = result['additional_info']['vehicle']['owner']['geo'][
        'region'] if 'region' in result['additional_info']['vehicle']['owner']['geo'] else ''

    city_reg = 'найдено' if 'city' in result['additional_info']['vehicle']['owner']['geo'] else 'не найдено'
    city_reg_db = result['additional_info']['vehicle']['owner']['geo'][
        'city'] if 'city' in result['additional_info']['vehicle']['owner']['geo'] else ''

    if 'phone_number' in result['additional_info']['vehicle']['owner']:
        owner_phone = 'найдено'
        owner_phone_db = result['additional_info']['vehicle']['owner']['phone_number']

    elif int(result['registration_actions']['count']) > 0:
        for item in result['registration_actions']['items']:
            __phone = item['owner']['phone_number'] if 'phone_number' in item['owner'] else None
            if __phone != None:
                owner_phone = 'найдено'
                owner_phone_db = __phone
                break
            owner_phone = 'не найдено'
            owner_phone_db = ''
    else:
        owner_phone = 'не найдено'
        owner_phone_db = ''

    info_owner = {
        'area_reg': area_reg_db,
        'city_reg': city_reg_db,
        'owner_phone': owner_phone_db
    }

    if subscribe:
        vin = result['identifiers']['vehicle']['vin'] if 'vin' in result['identifiers']['vehicle'] else 'нет данных'
        reg = result['identifiers']['vehicle']['reg_num'] if 'reg_num' in result['identifiers']['vehicle'] else 'нет данных'
        owner_count = result['ownership']['history']['count'] if 'count' in result['ownership']['history'] else 'нет данных'
        dtp_count = result['accidents']['history']['count'] if 'count' in result['accidents']['history'] else 'нет данных'
        mileages_count = result['mileages']['count'] if 'count' in result['mileages'] else 'нет данных'

    else:
        vin = 'найдено' if 'vin' in result['identifiers']['vehicle'] else 'не найдено'
        reg = 'найдено' if 'reg_num' in result['identifiers']['vehicle'] else 'не найдено'
        owner_count = 'найдено' if 'count' in result['ownership']['history'] else 'не найдено'
        dtp_count = 'найдено' if 'count' in result['accidents']['history'] else 'не найдено'
        mileages_count = 'найдено' if 'count' in result['mileages'] else 'не найдено'

    type_check = all_info['result']['content']['query']['type']
    msg = "#️⃣\n"
    if type_check == "VIN":
        msg += f"└ <b>VIN:</b> <code>{number}</code>\n\n"
    else:
        msg += f"└ <b>Номер:</b> <code>{number}</code>\n\n"

    msg += f"<b>На данный момент сервис ОСАГО недоступен</b>\n"
    msg += f"<b>Детальная информация доступна в техническом отчете</b>\n"
    msg += f"<i>Информации о владельце нет</i>\n"
    msg += f"├ <b>VIN:</b> <code>{vin}</code>\n"
    msg += f"└ <b>Г/н:</b> <code>{reg}</code>\n\n"

    msg += f"📃 <b>Владельцы</b>\n"
    msg += f"└ <b>Колличество:</b> <code>{owner_count}</code>\n\n"

    msg += f"🚔 <b>ДТП</b>\n"
    msg += f"└ <b>Колличество:</b> <code>{dtp_count}</code>\n\n"

    msg += f"🗺 <b>История пробега</b>\n"
    msg += f"└ <b>Колличество:</b> <code>{mileages_count}</code>\n\n"

    user_rights_bool = await check_rights(user_id)
    if user_rights_bool == 1 or user_rights_bool == 2 or user_rights_bool == 0:
        if info_owner['area_reg'] != '' or info_owner['city_reg'] != '' or info_owner['owner_phone'] != '':
            msg += f"👨‍🦰 <b>Данные о владельце</b>\n"
            if info_owner['area_reg'] != '':
                msg += f"├ <b>Район регистрации:</b> <code>{area_reg}</code>\n"
            if info_owner['city_reg'] != '':
                msg += f"├ <b>Город регистрации:</b> <code>{city_reg}</code>\n"
            if info_owner['owner_phone'] != '':
                msg += f"└ <b>Номер телефона:</b> <code>{owner_phone}</code> (50/50)\n\n"

    photo = []
    if subscribe:
        if int(result["images"]['photos']['count']) > 0:
            count = 0
            for item in result["images"]['photos']['items']:
                if count == 5:
                    break
                photo.append(item["uri"])
                count += 1

    response = {"msg": msg, "photo": photo, "subscribe": subscribe,
                'uuid': all_info['result']['uuid'], 'info_owner': info_owner}
    return response


async def check_auto(number, user_id):
    all_info = await main_mini(number)
    if 'error' in all_info:
        return all_info
    if not 'osago' in all_info['result']['content']['content']['insurance']:
        error = {
            'error': '<b>Ошибка на стороне сервера.\nПопробуйте еще раз</b>'
        }
        return error
    async with DataBase() as db:
        subscribe = await db.read('subscribe', where="user_id={} AND status=true ORDER BY id DESC".format(user_id))
    with open('result.json', 'w', encoding='utf8') as file:
        json.dump(all_info, file, indent=4, ensure_ascii=False)

    result = all_info['result']['content']['content']
    number = number.upper()
    if int(result['insurance']['osago']['count']) > 0:
        return await yes_osago(all_info, subscribe, number, user_id)
    else:
        return await no_osago(all_info, subscribe, number, user_id)


@dp.message_handler(IsNumber())
async def get_number(message: types.Message):
    chat_id = message.chat.id
    async with DataBase() as db:
        try:
            auth = await db.read('users', where="user_id={}".format(chat_id))
            if auth:
                user_rights_bool = await check_rights(chat_id)
                await message.answer(f"⏳ <b>Получаем информацию...</b>", parse_mode=types.ParseMode.HTML)
                result = await check_auto(message.text, chat_id)
                try:
                    await bot.delete_message(chat_id, message.message_id+1)
                    await bot.delete_message(chat_id, message.message_id+2)
                except:
                    pass
                if 'error' in result:
                    msg = '❌ '+result['error']
                    await message.answer(msg, parse_mode=types.ParseMode.HTML)
                    return
                await db.increment("users", "checked_auto", 1, where=f"user_id={chat_id}")
                info_owner = result['info_owner']
                id_avtocod = result['uuid']
                await db.insert('history', ["user_id", "request_type", "request", "id_avtocod", "info_owner"], [chat_id, "check_auto", message.text, id_avtocod, str(info_owner)])
                inline_btn_1 = InlineKeyboardButton(
                    "💳 Оформить подписку", callback_data="pay_subcribe")
                query = await db.read('users', where="user_id={}".format(chat_id))
                free_otchet = query[0]['free_otchet']
                inline_btn_2 = InlineKeyboardButton(
                    f"🔧 Технический отчет - {price_otchet}₽", callback_data="otchet_"+result['uuid']+'_'+message.text)

                if free_otchet != 0:
                    inline_btn_2 = InlineKeyboardButton(
                        f"🔧 Технический отчет - 0₽", callback_data="otchet_"+result['uuid']+'_'+message.text)

                inline_kb1 = InlineKeyboardMarkup()
                if result["subscribe"]:
                    inline_kb1.row(inline_btn_2)
                else:
                    inline_kb1.row(inline_btn_1).row(inline_btn_2)
                if user_rights_bool == 1 or user_rights_bool == 2 or user_rights_bool == 0:
                    if info_owner['area_reg'] != '':
                        area = InlineKeyboardButton(
                            f"📡 Узнать область - {str(price_area)}₽", callback_data="get_area_"+id_avtocod)
                        inline_kb1.row(area)
                    if info_owner['city_reg'] != '':
                        city = InlineKeyboardButton(
                            f"🌇 Узнать город - {str(price_city)}₽", callback_data="get_city_"+id_avtocod)
                        inline_kb1.row(city)
                    if info_owner['owner_phone'] != '':
                        phone = InlineKeyboardButton(
                            f"📱 Узнать телефон - {str(price_phone)}₽", callback_data="get_phone_"+id_avtocod)
                        inline_kb1.row(phone)
                await message.answer(result["msg"], reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
                media = []
                for item in result["photo"]:
                    media.append(types.InputMediaPhoto(item, message.text))
                if len(media) > 0:
                    await types.ChatActions.upload_photo()
                    await bot.send_media_group(message.chat.id, media=media)
            else:
                await message.answer("🤔 <b>Вы не зарегистрированы. Введите команду /start и повторите регистрацию</b>", parse_mode=types.ParseMode.HTML, )
        except Exception as exc:
            await sendError(message)


@dp.callback_query_handler(lambda c: c.data.split('_')[0] == 'otchet')
async def otchet(call: types.CallbackQuery):
    try:
        async with DataBase() as db:
            user_id = call.message.chat.id
            number_str = call.data.split('_')[1]
            number_str_text = call.data.split('_')[2]
            query = await db.read('users', where="user_id={}".format(user_id))
            balance = int(query[0]["balance"])
            free_otchet = query[0]['free_otchet']
            link = 'https://profi.avtocod.ru/report/guest/'+number_str
            msg = f'📝 Отчет АвтоКод по номеру <code>{number_str_text.upper()}</code> был успешно сгенерирован.\n\n'
            msg += f'Ознакомиться с отчетом можно по ссылке ниже:\n\n'
            msg += link
            favorite = InlineKeyboardButton(
                "⭐️ В избранное", callback_data="add_fav|"+number_str+"|"+number_str_text.upper())
            inline_kb1 = InlineKeyboardMarkup().row(favorite)
            if free_otchet == 0:
                if balance >= price_otchet:
                    await db.decrement("users", "balance", price_otchet, where=f"user_id={user_id}")
                    await db.insert('operations', ['user_id', 'transaction_type', 'transaction'], [user_id, 'writedowns', f'{price_otchet}₽ - Покупка отчета по автомобилю {number_str_text.upper()}'])
                else:
                    msg = "❌ На вашем счету недостаточно средств!\n"
                    msg += "- - - - - - - - - - - - - -\n"
                    msg += f"<b>Ваш баланс:</b> <code>{balance}₽</code>"
                    inline_btn_1 = InlineKeyboardButton(
                        f"💳 Пополнить баланс на сумму {price_otchet-balance} ₽", callback_data="payment_" + str(price_otchet - balance))
                    cancel = InlineKeyboardButton(
                        "❌ Закрыть", callback_data="cancel")
                    inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1).add(cancel)
            else:
                await db.decrement("users", "free_otchet", 1, where=f"user_id={user_id}")
            await call.message.answer(msg, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
    except Exception as exc:
        await sendError(call.message)


@dp.message_handler(content_types=["photo"])
async def handle_docs_photo(message: types.Message):
    chat_id = message.chat.id
    async with DataBase() as db:
        try:
            auth = await db.read('users', where="user_id={}".format(chat_id))
            if auth:
                await message.photo[-1].download("auto.jpg")
                image = open("auto.jpg", "rb")
                image_read = image.read()
                image_64_encode = base64.encodebytes(image_read)
                result = json.loads(
                    requests.post(
                        "https://data.av100.ru/numberrecognize.ashx?key=",
                        data={"img": image_64_encode},
                    ).text
                )
                if result["result"]:
                    message.text = result["result"][0]
                    await get_number(message)
                else:
                    msg = "❌ <b>Не удалось определить номер!</b>\n\n"
                    msg += "Попробуйте другую фотографию или отправьте номер авто."
                    await message.reply(msg, parse_mode=types.ParseMode.HTML)
            else:
                await message.answer(
                    "🤔 <b>Вы не зарегистрированы. Введите команду /start и повторите регистрацию</b>",
                    parse_mode=types.ParseMode.HTML,
                )
        except Exception as exc:
            await sendError(message)


@dp.callback_query_handler(lambda c: c.data.split('|')[0] == 'add_fav')
async def _add_favorite(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        async with DataBase() as db:
            fav_id = call.data.split('|')[1]
            number = call.data.split('|')[2]
            await db.insert('favorites', ['user_id', 'number', 'favorite_id'], [chat_id, number, fav_id])
            await call.answer('Успешно добавлено в избранное', show_alert=False)
            await bot.edit_message_text(call.message.text, chat_id, message_id)
    except Exception as exc:
        await sendError(call.message)
