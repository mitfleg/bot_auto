import os
from aiogram.dispatcher.filters import Filter
import asyncio
import uuid
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
from .common import get_month, getBalance, plural_days, getConfig, format_datetime, ADMIN_ID, get_grouped_items, format_history_item, main_menu_all
from handlers.db import DataBase
from yookassa import Configuration, Payment
from bot import dp, bot
from datetime import datetime, timedelta
import traceback
from .savehtml import save_html

kassa = getConfig('yookassa')
Configuration.account_id = kassa['account_id']
Configuration.secret_key = kassa['secret_key']


async def payment_link(pay_sum, user_id, period=None):
    payment = Payment.create({
        "amount": {
            "value": pay_sum,
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/avto_check_bot"
        },
        "capture": True,
        "description": "Пополнение баланса. ID пользователя: "+str(user_id)
    }, uuid.uuid4())
    key = payment.id
    status = payment.status
    async with DataBase() as db:
        if period:
            await db.insert('payment', ["user_id", "sum", "pay_key", "pay_type", "status"], [user_id, pay_sum, key, 'subscribe_'+period, status])
        else:
            await db.insert('payment', ["user_id", "sum", "pay_key", "pay_type", "status"], [user_id, pay_sum, key, 'balance', status])
    result = {
        'id': payment.id,
        'link': payment.confirmation.confirmation_url
    }
    return result


async def buy_subscribe(chat_id, period):
    period = int(period)
    if period == 20:
        clock_in_half_hour = datetime.now() + timedelta(minutes=20)
        period_str = '20 минут'
        price = 50
    if period == 1:
        clock_in_half_hour = datetime.now() + timedelta(days=1)
        period_str = '1 день'
        price = 75
    if period == 7:
        clock_in_half_hour = datetime.now() + timedelta(days=7)
        period_str = '7 дней'
        price = 200
    if period == 30:
        clock_in_half_hour = datetime.now() + timedelta(days=30)
        period_str = '30 дней'
        price = 400
    if period == 180:
        clock_in_half_hour = datetime.now() + timedelta(days=180)
        period_str = '180 дней'
        price = 2000
    if period == 360:
        clock_in_half_hour = datetime.now() + timedelta(days=360)
        period_str = '360 дней'
        price = 3500

    async with DataBase() as db:
        sql = "INSERT INTO subscribe (`user_id`, `date_from`, `date_to`,`period`,`status`) VALUES (%s, %s, %s, %s, %s)"
        await db.execute_query(sql, (chat_id, datetime.now(), clock_in_half_hour, period_str, True))
        query = await db.read('users', where="user_id={}".format(chat_id))
        balance = query[0]['balance']
        new_balance = balance-price
        await db.update('users', ['user_subcribe_end', 'balance'], [clock_in_half_hour, new_balance], where="user_id={}".format(chat_id))


async def sendError(message):
    try:
        await bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    async with DataBase() as db:
        query = await db.read('users', where="user_id={}".format(message.chat.id))
        user_info = query[0]
        user_name = user_info['user_name']
        print(traceback.format_exc())
        await bot.send_message(ADMIN_ID, traceback.format_exc())
        await bot.send_message(ADMIN_ID, '@'+user_name)
        msg = '⛔️ Произошла ошибка.\nПопробуйте снова.'
        await message.answer(msg, parse_mode=types.ParseMode.HTML)


@dp.callback_query_handler(text="account")
async def account(call: types.CallbackQuery):
    message_id = call.message.message_id
    chat_id = call.message.chat.id
    try:
        async with DataBase() as db:
            query = await db.read('users', where="user_id={}".format(chat_id))
            account_info = query[0]
            user_id = account_info['user_id']
            user_phone = account_info['user_phone']
            date_created = account_info['date_created'].strftime('%d.%m.%Y')
            day, month, year = date_created.split('.')
            date_temp = datetime(int(year), int(month), int(day))
            now_date = datetime.now()
            date_diff = now_date - date_temp
            date_diff = date_diff.days if date_diff.days > 0 else 1
            balance = account_info['balance']
            checked_auto = account_info['checked_auto']
            user_subcribe = 'отсутствует'
            if account_info['user_subcribe_end'] != None:
                query = await db.read('subscribe', where="user_id={} AND status=true ORDER BY id DESC".format(chat_id))
                user_subcribe = query[0]
                user_subcribe = format_datetime(str(user_subcribe['date_to']))
            bot_name = await bot.get_me()
            bot_name = bot_name['username']
            msg = '<b>Мой аккаунт</b>\n'
            msg += '<i>Вся необходимая информация о вашем профиле</i>\n\n'
            msg += f'👁‍🗨 <b>ID</b>: <code> {user_id}</code>\n'
            msg += f'👁‍🗨 <b>Телефон</b>: <code> {user_phone}</code>\n'
            msg += f'👁‍🗨 <b>Регистрация</b>: <code> {date_created} ({plural_days(date_diff)})</code>\n\n'

            msg += f'💶 <b>Мой кошелёк</b>: <code> {balance}₽</code>\n'
            msg += f'📝 <b>Подписка до</b>: <code> {user_subcribe}</code>\n\n'

            #msg += f'⤵️ <b>Реферальная ссылка</b>:\n'
            #msg += f'└ <code> https://t.me/{bot_name}?start={chat_id}</code>\n\n'

            msg += f'🔎 <b>Моя статистика запросов</b>:\n'
            msg += f'<b>└ Автомобилей:</b> <code> {checked_auto}</code>\n'

            inline_kb1 = InlineKeyboardMarkup()
            inline_btn_1 = InlineKeyboardButton(
                '📝 Управление подпиской', callback_data='subcribe')
            inline_kb1.add(inline_btn_1)
            inline_btn_2 = InlineKeyboardButton(
                '🧾 Операции', callback_data='operations')
            inline_btn_3 = InlineKeyboardButton(
                '📥 Пополнить', callback_data='payment')
            inline_kb1.row(inline_btn_2, inline_btn_3)
            inline_btn_4 = InlineKeyboardButton(
                '📁 История поиска', callback_data='history')
            inline_kb1.row(inline_btn_4)
            inline_btn_5 = InlineKeyboardButton(
                '⭐️ Избранное', callback_data='all_favorites')
            inline_kb1.add(inline_btn_5)
            back = InlineKeyboardButton(
                '🔙 Назад', callback_data='back|mainmenu')
            inline_kb1.add(back)
            await bot.edit_message_text(msg, chat_id, message_id, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text="payment")
async def payment_msg(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        msg = '<b>Пополнение баланса</b>\n'
        msg += '<i>Введите сумму на которую хотите пополнить Ваш баланс или выберите из предложенных</i>\n\n'
        inline_btn_1 = InlineKeyboardButton(
            '100₽', callback_data='payment_100')
        inline_btn_2 = InlineKeyboardButton(
            '250₽', callback_data='payment_250')
        inline_btn_3 = InlineKeyboardButton(
            '500₽', callback_data='payment_500')
        inline_btn_4 = InlineKeyboardButton(
            '1000₽', callback_data='payment_1000')
        back = InlineKeyboardButton(
            '🔙 Назад', callback_data='back|account')
        inline_kb1 = InlineKeyboardMarkup().row(inline_btn_1, inline_btn_2).row(
            inline_btn_3, inline_btn_4).add(back)
        await bot.edit_message_text(msg, chat_id, message_id, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text=['payment_100', 'payment_250', 'payment_500', 'payment_1000'])
async def payment_callback(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        summ = call.data.split('_')[1]
        payment_info = await payment_link(summ, chat_id)
        inline_btn_1 = InlineKeyboardButton(
            text="Оплатить", url=payment_info['link'])
        inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1)
        msg = f'💳 Для пополнения счета на <code>{summ}₽</code> <b>перейдите по ссылке:</b>\n'
        msg += 'Данное сообщение <b>автоматически</b> удалится через минуту'
        await call.message.answer(msg, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
        try:
            await call.message.delete()
        except:
            pass
        await asyncio.sleep(60)
        try:
            await bot.delete_message(chat_id, message_id+1)
        except:
            pass
    except Exception as exc:
        await sendError(call.message)


@dp.message_handler(lambda message: message.text.isdigit())
async def payment_text(message: types.Message):
    try:
        summ = message.text
        phone = [
            r"^((\+7|7|8)+([0-9]){10})$",
            r"^(\+)?((\d{2,3}) ?\d|\d)(([ -]?\d)|( ?(\d{2,3}) ?)){5,12}\d$",
        ]

        regexps_compiled = [re.compile(r) for r in phone]
        for regex in regexps_compiled:
            if re.findall(regex, summ):
                await message.answer('Сервис в разработке.')
                return False
        link = await payment_link(summ, message.chat.id)
        inline_btn_1 = InlineKeyboardButton(text="Оплатить", url=link['link'])
        inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1)
        msg = f'💳 Для пополнения счета на <code>{summ}₽</code> <b>перейдите по ссылке:</b>\n'
        msg += 'Данное сообщение <b>автоматически</b> удалится через минуту'
        await message.answer(msg, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
        await asyncio.sleep(60)
        try:
            await bot.delete_message(message.chat.id, message.message_id+1)
        except:
            pass
    except Exception as exc:
        await sendError(message)


@dp.callback_query_handler(text='change_summ')
async def change_summ(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        msg = '<b>Пополнение баланса</b>\n'
        msg += '<i>Введите сумму на которую хотите пополнить Ваш баланс или выберете из предложенных</i>\n\n'
        inline_btn_1 = InlineKeyboardButton(
            '100₽', callback_data='payment_100')
        inline_btn_2 = InlineKeyboardButton(
            '250₽', callback_data='payment_250')
        inline_btn_3 = InlineKeyboardButton(
            '500₽', callback_data='payment_500')
        inline_btn_4 = InlineKeyboardButton(
            '1000₽', callback_data='payment_1000')
        back = InlineKeyboardButton('🔙 Назад', callback_data='back|account')
        inline_kb1 = InlineKeyboardMarkup().row(inline_btn_1, inline_btn_2).row(
            inline_btn_3, inline_btn_4).add(back)
        await bot.edit_message_text(msg, chat_id, message_id, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text="history")
async def history(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        async with DataBase() as db:
            history = await db.read('history', where="user_id={} ORDER BY date_created DESC".format(chat_id))
            if history:
                msg = '<b>История поисков</b>\n'
                msg += '<i>Функция сохраняет сведения о Ваших запросах в поисковой системе</i>\n\n'
                grouped_items = get_grouped_items(history)
                count = 0
                for item_global in grouped_items:
                    if count == 10:
                        break
                    date_created = grouped_items[item_global][0]['date_created']
                    date_str = format_datetime(str(date_created), short=True)
                    msg += f'<b>{date_str}</b>\n'
                    for item in grouped_items[item_global]:
                        if count == 10:
                            break
                        msg += format_history_item(item) + '\n'
                        count += 1
                inline_btn_1 = InlineKeyboardButton(
                    'Показать всю историю', callback_data='all_history')
                inline_btn_2 = InlineKeyboardButton(
                    'Очистить', callback_data='clear_history')
                back = InlineKeyboardButton(
                    '🔙 Назад', callback_data='back|account')
                inline_kb1 = InlineKeyboardMarkup().row(inline_btn_1, inline_btn_2).add(back)
                await bot.edit_message_text(msg, call.message.chat.id, message_id, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
            else:
                await call.answer('⛔️ История не найдена', show_alert=True)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text="all_history")
async def all_history(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        async with DataBase() as db:
            history = await db.read('history', where="user_id={} ORDER BY date_created DESC".format(user_id))
            if history:
                grouped_items = get_grouped_items(history)
                doc = save_html(grouped_items, 'История поисков')
                cancel = InlineKeyboardButton(
                    '❌ Закрыть', callback_data='cancel')
                inline_kb1 = InlineKeyboardMarkup().row(cancel)
                await bot.send_document(user_id, open(doc, 'rb'), caption='📁 Ответ на <b>Ваш запрос</b> получился достаточно внушительного размера и отправить его через телеграм можно только в виде файла', reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
                os.remove(doc)
            else:
                await call.answer('⛔️ История не найдена', show_alert=True)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text="clear_history")
async def clear_history_question(call: types.CallbackQuery):
    message_id = call.message.message_id
    try:
        msg = "🗑 <b>Удалить историю?</b>"
        inline_btn_1 = InlineKeyboardButton(
            '✅ Да', callback_data='clear_history_yes')
        inline_btn_2 = InlineKeyboardButton(
            '❌ Нет', callback_data='clear_history_no')
        inline_kb1 = InlineKeyboardMarkup().row(inline_btn_1, inline_btn_2)
        await bot.edit_message_text(msg, call.message.chat.id, message_id, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text="clear_history_yes")
async def clear_history_yes(call: types.CallbackQuery):
    async with DataBase() as db:
        await db.delete('history', where="user_id={}".format(call.message.chat.id))
        await call.answer('🗑 История удалена', show_alert=True)
        result = await main_menu_all(call.message)
        try:
            await bot.edit_message_text(result['msg'], call.message.chat.id, call.message.message_id, reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)
        except:
            await call.message.answer(result['msg'], reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)


@dp.callback_query_handler(text="clear_history_no")
async def clear_history_yes(call: types.CallbackQuery):
    await history(call)


@dp.callback_query_handler(text=["subcribe", "pay_subcribe"])
async def subcribe(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        async with DataBase() as db:
            query = await db.read('subscribe', where="user_id={} AND status=true ORDER BY id DESC".format(chat_id))
            if query:
                subscribe = query[0]
                date_end = subscribe['date_to']
                date = date_end.strftime('%d')
                year = date_end.strftime('%Y')
                if int(date_end.strftime('%m')) != 10:
                    month = int(date_end.strftime('%m').replace('0', ''))
                else:
                    month = int(date_end.strftime('%m'))
                time = date_end.strftime('%H:%M')
                msg = '<b>Управление подпиской</b>\n\n'
                msg += 'Подписка активна.\n'
                msg += 'Период действия до <b>'+date+' ' + \
                    get_month(month-1) + ' ' + year + ' '+time+'</b>\n'
                cancel = InlineKeyboardButton(
                    '🔙 Назад', callback_data='back|account')
                inline_kb1 = InlineKeyboardMarkup().add(cancel)
            else:
                msg = '<b>Управление подпиской</b>\n'
                msg += '<i>Подписка обеспечивает доступ ко всем функциям, быстрой обработки данных.</i>\n\n'

                inline_btn_1 = InlineKeyboardButton(
                    '50₽ за 20 минут', callback_data='subscribe_50')
                inline_btn_2 = InlineKeyboardButton(
                    '75₽ за 1 день', callback_data='subscribe_75')
                inline_btn_3 = InlineKeyboardButton(
                    '200₽ за 7 дней', callback_data='subscribe_200')
                inline_btn_4 = InlineKeyboardButton(
                    '400₽ за 30 дней', callback_data='subscribe_400')
                inline_btn_5 = InlineKeyboardButton(
                    '2000₽ за 180 дней', callback_data='subscribe_2000')
                inline_btn_6 = InlineKeyboardButton(
                    '3500₽ за 360 дней', callback_data='subscribe_3500')
                cancel = InlineKeyboardButton(
                    '🔙 Назад', callback_data='back|account')
                inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1).row(inline_btn_2,
                                                                          inline_btn_3).row(inline_btn_4, inline_btn_5).add(inline_btn_6).add(cancel)
            try:
                type_response = call.data.split('|')[1]
            except:
                type_response = ''
            if call.data == 'subcribe' or type_response == 'subcribe':
                await bot.edit_message_text(msg, call.message.chat.id, message_id, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
            else:
                await call.message.answer(msg, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text=['subscribe_50', 'subscribe_75', 'subscribe_200', 'subscribe_400', 'subscribe_2000', 'subscribe_3500'])
async def payment_subcribe(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        balance = await getBalance(chat_id)
        price_subscribe = int(call.data.split('_')[1])
        if price_subscribe == 50:
            period = 20
            period_str = '20 минут'
        elif price_subscribe == 75:
            period = 1
            period_str = '1 день'
        elif price_subscribe == 200:
            period = 7
            period_str = '7 дней'
        elif price_subscribe == 400:
            period = 30
            period_str = '30 дней'
        elif price_subscribe == 2000:
            period = 180
            period_str = '180 дней'
        elif price_subscribe == 3500:
            period = 360
            period_str = '360 дней'
        else:
            period = 0
        if balance >= price_subscribe:
            await buy_subscribe(chat_id, period)
            msg = '✅ <b>Оформление подписки!</b>\n'
            msg += '<b>└ Период действия:</b> <code>'+period_str+'</code>\n'
            await call.message.answer(msg, parse_mode=types.ParseMode.HTML)
        else:
            msg = '❌ На вашем счету недостаточно средств!\n'
            msg += '- - - - - - - - - - - - - -\n'
            msg += f'<b>Ваш баланс:</b> <code>{balance}₽</code>'
            inline_btn_1 = InlineKeyboardButton(
                f'💳 Пополнить баланс на сумму {price_subscribe - balance} ₽', callback_data='payment_'+str(price_subscribe - balance)+'_'+str(period))
            back = InlineKeyboardButton(
                '🔙 Назад', callback_data='back|subcribe')
            inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1).add(back)
            await call.message.answer(msg, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
        try:
            await bot.delete_message(chat_id, message_id)
        except:
            pass
        result = await main_menu_all(call.message)
        await call.message.answer(result['msg'], reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text="operations")
async def operations(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        async with DataBase() as db:
            operations = await db.read('operations', where="user_id={} ORDER BY date_created DESC".format(chat_id))
            if operations:
                msg = '<b>Последние операции</b>\n'
                msg += '<i>Вы можете просмотреть список совершенных Вами операций</i>\n\n'
                grouped_items = get_grouped_items(operations)
                count = 0
                for item_global in grouped_items:
                    if count == 10:
                        break
                    date_created = grouped_items[item_global][0]['date_created']
                    date_str = format_datetime(str(date_created), short=True)
                    msg += f'<b>{date_str}</b>\n'
                    for item in grouped_items[item_global]:
                        if count == 10:
                            break
                        msg += format_history_item(item, operation=True) + '\n'
                        count += 1
                    msg += '\n'
                inline_btn_1 = InlineKeyboardButton(
                    'Показать все операции', callback_data='all_operations')
                back = InlineKeyboardButton(
                    '🔙 Назад', callback_data='back|account')
                inline_kb1 = InlineKeyboardMarkup().row(inline_btn_1).add(back)
                await bot.edit_message_text(msg, call.message.chat.id, message_id, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
            else:
                await call.answer('⛔️ Операции не найдены', show_alert=True)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text="all_operations")
async def all_operations(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    try:
        async with DataBase() as db:
            operations = await db.read('operations', where="user_id={} ORDER BY date_created DESC".format(chat_id))

            if operations:
                grouped_items = get_grouped_items(operations)
                doc = save_html(
                    grouped_items, 'Финансовые операции', is_operation=True)
                cancel = InlineKeyboardButton(
                    '❌ Закрыть', callback_data='cancel')
                inline_kb1 = InlineKeyboardMarkup().row(cancel)
                await bot.send_document(chat_id, open(doc, 'rb'), caption='📁 Ответ на <b>Ваш запрос</b> получился достаточно внушительного размера и отправить его через телеграм можно только в виде файла', reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
                os.remove(doc)
            else:
                await call.answer('⛔️ Операции не найдены', show_alert=True)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text="all_favorites")
async def all_favorites_info(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        async with DataBase() as db:
            all_favorites = await db.read('favorites', where="user_id={}".format(chat_id))
            if all_favorites:
                msg = '⭐️ <b>Список избранного</b>\n'
                for item in all_favorites:
                    msg += f"ID: <code> {item['id']}</code>\n"
                    msg += f"Номер ТС: <code> {item['number']}</code>\n"
                    msg += f"Ссылка на отчет: https://profi.avtocod.ru/report/guest/{item['favorite_id']}\n\n"
                inline_kb1 = InlineKeyboardMarkup()
                delete_fav = InlineKeyboardButton(
                    '🗑 Удалить из избранного', callback_data='delete_fav')
                back = InlineKeyboardButton(
                    '🔙 Назад', callback_data='back|account')
                inline_kb1.add(delete_fav).add(back)
                await bot.edit_message_text(msg, chat_id, message_id, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
            else:
                await call.answer('🔍 Папка с избранным пуста', show_alert=True)
                result = await main_menu_all(call.message)
                try:
                    await bot.edit_message_text(result['msg'], call.message.chat.id, message_id, reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)
                except:
                    await call.message.answer(result['msg'], reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text="delete_fav")
async def __dell_favorites(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        async with DataBase() as db:
            all_favorites = await db.read('favorites', where="user_id={}".format(chat_id))
            if all_favorites:
                msg = '🗑 <b>ID записи для удаления</b>\n'
                msg += 'После удаления, восстановление <b>невозможно!</b>\n'
                inline_kb1 = InlineKeyboardMarkup(row_width=3)
                for item in all_favorites:
                    btn = InlineKeyboardButton(
                        item['number']+f" [ID:{str(item['id'])}]", callback_data='delete_fav|'+str(item['id']))
                    inline_kb1.insert(btn)
                delete_all = InlineKeyboardButton(
                    '🗑 Удалить все', callback_data='delete_fav|all')
                back = InlineKeyboardButton(
                    '🔙 Назад', callback_data='back|all_favorites')
                inline_kb1.row(delete_all)
                inline_kb1.row(back)
                await bot.edit_message_text(msg, chat_id, message_id, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
            else:
                await call.answer('🔍 Папка с избранным пуста', show_alert=True)
                result = await main_menu_all(call.message)
                try:
                    await bot.edit_message_text(result['msg'], call.message.chat.id, message_id, reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)
                except:
                    await call.message.answer(result['msg'], reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(lambda c: c.data.split('|')[0] == 'delete_fav')
async def __dell_favorites_id(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    try:
        id_fav = call.data.split('|')[1]
        async with DataBase() as db:
            if id_fav == 'all':
                await db.delete('favorites', where="user_id={}".format(chat_id))
            else:
                await db.delete('favorites', where="id={}".format(id_fav))
        await __dell_favorites(call)
        await call.answer('Успешно удалено', show_alert=False)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(text="cancel")
async def cancel(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(lambda c: c.data.split('_')[0] == 'payment')
async def payment_sub(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        message = call.data
        summ = message.split('_')[1]
        try:
            period = message.split('_')[2]
            paymentInfo = await payment_link(summ, call.message.chat.id, period)
        except:
            paymentInfo = await payment_link(summ, call.message.chat.id)
        inline_btn_1 = InlineKeyboardButton(
            text="Оплатить", url=paymentInfo['link'])
        inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1)
        msg = f'💳 Для пополнения счета на <code>{summ}₽</code> <b>перейдите по ссылке:</b>\n'
        msg += 'Данное сообщение <b>автоматически</b> удалится через минуту'
        await call.message.answer(msg, reply_markup=inline_kb1, parse_mode=types.ParseMode.HTML)
        try:
            await call.message.delete()
        except:
            pass
        await asyncio.sleep(60)
        try:
            await bot.delete_message(chat_id, message_id+1)
        except:
            pass
    except Exception as exc:
        await sendError(call.message)


@dp.callback_query_handler(lambda c: c.data.split('|')[0] == 'back')
async def back_account(call: types.CallbackQuery):
    back_url = call.data.split('|')[1]
    if back_url == 'account':
        await account(call)
    if back_url == 'mainmenu':
        result = await main_menu_all(call.message)
        try:
            await bot.edit_message_text(result['msg'], call.message.chat.id, call.message.message_id, reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)
        except:
            await call.message.answer(result['msg'], reply_markup=result['btns'], parse_mode=types.ParseMode.HTML)
    if back_url == 'change_summ':
        payment_id = call.data.split('|')[2]
        async with DataBase() as db:
            await db.delete('payment', where="pay_key={}".format(payment_id))
        await change_summ(call)
    if back_url == 'all_favorites':
        await all_favorites_info(call)
    if back_url == 'subcribe':
        try:
            payment_id = call.data.split('|')[2]
            async with DataBase() as db:
                await db.delete('payment', where="pay_key={}".format(payment_id))
        except:
            pass
        await subcribe(call)
    if back_url == 'help':
        from .help import help
        await help(call)
