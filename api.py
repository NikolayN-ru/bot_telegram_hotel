import os
import requests
import datetime
from request_data import Request
from loguru import logger
from request_exeption import ResponseError
from typing import Union, List
from environs import Env
from math import ceil
import json


env = Env()
env.read_env()
api = env('API_KEY')


headers = {
    'x-rapidapi-key': api,
    'x-rapidapi-host': "hotels4.p.rapidapi.com"}


url2 = "https://hotels4.p.rapidapi.com/properties/list"


def search_town(town: str) -> Union[List, str]:

    '''Данная функция принимает на вход название города(на русском языке)
    и возвращает список с результатами поиска .
     Для этого она отправляет GET-запрос и извлекает список найденных городов'''

    url = "https://hotels4.p.rapidapi.com/locations/search"
    querystring = {"query": town,
                   "locale": 'ru_Ru'
                       }
    try:
        response = requests.request("GET", url, headers=headers, params=querystring)
        results = response.json()['term']
        print(results)
        town_list = [{}]
        town_list[0]['term'] = results
        print(town_list)
        return town_list
    except BaseException as err:
        logger.critical(f'Searchrequests.search_town: - {err}')
        return 'error'


# @logger.catch()
# def id_search(city: str, locale: str ='ru_RU') -> list:
#     print('id_search_city: '+city)
#     '''Функция используется для получения идентификатора места назначения.
#      Для этого она отправляет запрос  и передает ему название города и языковые настройки.
#     Ответ возвращается в формате JSON, и из него извлекается идентификатор места назначения,
#     который потом используется для поиска отелей.
#     Если в ответе не удалось найти идентификатор, функция выбрасывает исключение ResponseError.'''
#
#     logger.warning(f'city: {city}')
#     params = {"q": city, "locale": locale}  # Параметры открывания страницы
#     print(params)
#     url = 'https://hotels4.p.rapidapi.com/locations/v3/search'
#     response = requests.get(url=url, headers=headers, params=params)
#     if response.status_code == 200:
#         return [(location.get('gaiaId', '0'), location['regionNames']['displayName']) for location in response.json()['sr']]
#     else:
#         raise ResponseError

@logger.catch()
def id_search(city: str, locale: str ='ru_RU') -> list:

    '''Функция используется для получения идентификатора места назначения.
     Для этого она отправляет запрос  и передает ему название города и языковые настройки.
    Ответ возвращается в формате JSON, и из него извлекается идентификатор места назначения,
    который потом используется для поиска отелей.
    Если в ответе не удалось найти идентификатор, функция выбрасывает исключение ResponseError.'''

    logger.warning(f'city: {city}')
    params = {"q": city, "locale": locale}

    url = 'https://hotels4.p.rapidapi.com/locations/v3/search'
    response = requests.get(url=url, headers=headers, params=params)

    data = response.json()
    # gaia_id = data["sr"][0]["gaiaId"]

    if response.status_code == 200:
        return [(location.get('gaiaId', '0'), location['regionNames']['displayName']) for location in
                response.json()['sr']]
        # return gaia_id
    else:
        raise ResponseError


@logger.catch()
def dates_range() -> tuple:

    '''Эта функция вычисляет диапазон дат для поиска отеля.
        Она вычисляет дату начала и дату окончания поиска.'''

    start_date = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    end_date = (datetime.date.today() + datetime.timedelta(days=2)).strftime('%Y-%m-%d')
    logger.warning(f'Дата ввода запроса {start_date} - {end_date}')
    return start_date, end_date


@logger.catch()
def get_hotels(request: Request, city: str = None, sort_order: str = None,
               price_min: int = None, price_max: int = None) -> str:

    '''Запрос к API Hotels для получения информации о доступных гостиницах в указанном городе. '''

    destination_id = id_search(city=city, locale='ru_RU')
    dates = dates_range()

    # querystring = {"destinationId": destination_id, "pageNumber": "1", "pageSize": request.search_results,
    #                "checkIn": dates[0], "checkOut": dates[1], "adults1": "1", "sortOrder": sort_order,
    #                "locale": 'ru_RU', "currency": "EUR"}
    querystring = {"destinationId": {"regionId": destination_id},
                   "checkInDate": {"day": 3, "month": 4, "year": 2023},
                   "checkOutDate": {"day": 4, "month": 4, "year": 2023},
                   "currency": "EUR",
                   "destination": {"regionId": "3000"},
                   "eapid": 1,
                   "filters": {"availableFilter": "SHOW_AVAILABLE_ONLY"},
                   "locale": "ru_RU",
                   "resultsSize": 3,
                   "resultsStartingIndex": 0,
                   "rooms": [{"adults": 1}],
                   "siteId": 300000001,
                   "sort": "PRICE_LOW_TO_HIGH"}
    if price_max and price_min:
        querystring['priceMin'] = f'{price_min}'
        querystring['priceMax'] = f'{price_max}'

    response = requests.request("POST", 'https://hotels4.p.rapidapi.com/properties/v2/list', headers=headers, json=querystring)

    if len(response.text['data']['propertySearch']['properties']) == 0:

        raise ResponseError
    num = 1
    result = ''

    for hotel in response['data']['body']['searchResults']['results']:

        '''Далее функция обрабатывает полученный ответ 
        и формирует результат в виде текстового сообщения 
        с информацией о каждой гостинице, которая подходит 
        по заданным параметрам. 
        В сообщении указываются навзание отеля, количество звезд, 
        адрес, расстояние от центра и цена.'''
        name = hotel['name']
        stars = '⭐' * int(ceil(hotel['starRating']))
        address = f"{hotel['address']['locality']}"
        distance = f"Distance from the center - {hotel['landmarks'][0]['distance']}"
        price = f"{hotel.get('ratePlan', {}).get('price', {}).get('current')} " \
                f"{hotel.get('ratePlan', {}).get('price', {}).get('info')}"
        if sort_order == "DISTANCE_FROM_LANDMARK":
            '''Этот блок кода проверяет, установлен ли параметр sort_order 
            в значение "DISTANCE_FROM_LANDMARK". 
            Если параметр установлен, то функция проверяет, 
            находится ли гостиница в заданной дистанции от центра города. 
            Если гостиница находится вне заданной дистанции, то функция переходит к 
            следующей гостинице.'''
            if hotel['landmarks'][0]['distance'] > request.distance:
                continue
        result += f"{num}. {name}\n{stars}\n{address}\n{distance}\n{price}\n\n"
        num += 1
    logger.warning(f'Done hotels search. Request: {request.chat_id}.')
    request.command = None
    request.city = None
    request.min_price = None
    request.max_price = None
    request.distance = None
    request.search_results = None
    request.destinationID = None
    return result


@logger.catch()
def low_price(request: Request) -> str:
    logger.warning(f'Returning the search result. Request: {request.chat_id}.')
    result = get_hotels(request=request, sort_order="PRICE")
    return result


@logger.catch()
def high_price(request: Request) -> str:
    logger.warning(f'Returning the search result. Request: {request.chat_id}.')
    result = get_hotels(request=request, sort_order="PRICE_HIGHEST_FIRST")
    return result


@logger.catch()
def best_deal(request: Request) -> str:
    logger.warning(f'Returning the search result. Request: {request.chat_id}.')
    result = get_hotels(request=request, sort_order="DISTANCE_FROM_LANDMARK", price_min=request.min_price,
                        price_max=request.max_price)
    return result


@logger.catch()
def history(filename: str, text: str) -> None:
    if not os.path.exists('history'):
        os.mkdir("history")
    path = os.path.abspath(os.path.join('history', filename))
    mode = 'a' if os.path.exists(path) else 'w'
    with open(path, mode, encoding='utf-8') as history:
        history.write(text)


def show_photos(cls, hotel: 'Hotel', number: int) -> 'Hotel':
    url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
    querystring = {"id": hotel.hotel_id}
    try:
        response = requests.request("GET", url, headers=headers, params=querystring)
        results = response.json()["hotelImages"]
        for i in range(number):
            hotel.url_photo.append(results[i]['baseUrl'].replace('{size}', results[i]['sizes'][0]['suffix']))
    except BaseException as err:
        logger.critical(f'Searchrequests.show_photo: - {err}')
    return hotel


def set_limits(cls, string: str) -> List:
    temp = []
    string = tuple(string.split())
    for item in string:
        if item.isdigit():
            temp.append(item)
    if len(temp) != 2:
        temp = []
    else:
        if int(temp[0]) > int(temp[1]):
            temp[0], temp[1] = temp[1], temp[0]
    return temp



