import asyncio
import requests
import json
from ..common import getConfig
import re
import os

main_conf = getConfig('auto')
login = main_conf['login']
password = main_conf['password']

async def auth():
    with open(os.getcwd()+'/headers.json') as file:
        headers = json.load(file)
    headers_auth = {
        'authority': 'api-profi.avtocod.ru',
        'accept': 'application/json',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'no-cache',
        'origin': 'https://profi.avtocod.ru',
        'referer': 'https://profi.avtocod.ru/',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="101", "Opera GX";v="87"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36 OPR/87.0.4390.58 (Edition Yx GX)',
    }
    json_data = {
        'jsonrpc': '2.0',
        'id': 2,
        'method': 'auth.login',
        'params': {
            'email': login,
            'password': password,
        },
    }
    token = requests.post('https://api-profi.avtocod.ru/rpc',
                          headers=headers_auth, json=json_data).json().get('result').get('token')
    headers['authorization'] = 'Bearer '+token
    with open(os.getcwd()+'/headers.json', 'w', encoding='utf8') as file:
        json.dump(dict(headers), file, indent=4, ensure_ascii=False)


async def get_result(json_data):
    with open(os.getcwd()+'/headers.json') as file:
        headers = json.load(file)
    json_data = json_data
    response = requests.post(
        'https://api-profi.avtocod.ru/rpc', headers=headers, json=json_data).json()
    return response


async def get_info_start(query, type_query):
    json_data = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'report.create',
        'params': {
            'query': query,
            'type': type_query,
        },
    }

    response = await get_result(json_data)
    if 'error' in response:
        await auth()
        response = await get_result(json_data)

    if 'uuid' in response.get('result'):
        uuid = response.get('result').get('uuid')
        link = 'https://profi.avtocod.ru/report/'+uuid
        result = {
            'link': link,
            'uuid': uuid
        }
    else:
        result = {
             'error': '<b>Ошибка на стороне сервера avtocode. Попробуйте снова</b>'
            }
    return result


async def get_full_info_mini(uuid):
    json_data = {
        'jsonrpc': '2.0',
        'id': 2,
        'method': 'report.upgrade',
        'params': {
            'uuid': uuid,
        },
    }

    await get_result(json_data)

    await asyncio.sleep(60)

    json_data = {
        'jsonrpc': '2.0',
        'id': 3,
        'method': 'report.get',
        'params': {
            'uuid': uuid,
        },
    }

    result = await get_result(json_data)
    if len(result['result']['content']) == 0:
        await asyncio.sleep(5)
        result = await get_result(json_data)

    osago_count = 0
    count_sleep = 0
    while osago_count == 0:
        if count_sleep == 5:
            error = {
                'error': '<b>Сервер не дал результата.</b>\nВозможные причины:\n1)Неверный номер\n2)Происходят обновления на сервере\n3)Сервис ГИБДД на данный момент недоступен\n<b>Рекомендуем повторить запрос позже</b>'
            }
            return error
        if 'result' in result:
            if 'content' in result['result']:
                if 'progress_ok' in result['result']['content']:
                    if int(result['result']['content']['progress_ok']) > 18:
                        return result
        else:
            result = await get_result(json_data)
        count_sleep += 1
        await asyncio.sleep(10)
    error = {
        'error': '<b>Сервер не дал результата.</b>\nВозможные причины:\n1)Неверный номер\n2)Происходят обновления на сервере\n3)Сервис ГИБДД на данный момент недоступен\n<b>Рекомендуем повторить запрос позже</b>'
    }
    return error


async def main_mini(query):
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
        if re.findall(regex, query):
            if re.findall(r"^(?i)[A-HJ-NPR-Z0-9]{17}", query):
                type_query = 'VIN'
            else:
                type_query = 'GRZ'
            result = await get_info_start(query, type_query)
            if 'error' in result:
                return result
            return await get_full_info_mini(result['uuid'])
