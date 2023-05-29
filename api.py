import os
import requests
import datetime
from request_data import Request
from loguru import logger
from request_exeption import ResponseError
from typing import Union, List
from environs import Env
from city import city as godCity

class Hotel:
    def __init__(self, name, rating, price):
        self.name = name
        self.rating = rating
        self.price = price

hotel1 = Hotel("Отель 1", 4.5, 100)
hotel2 = Hotel("Отель 2", 3.8, 80)
hotel3 = Hotel("Отель 3", 4.2, 120)

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
        town_list = [{}]
        town_list[0]['term'] = results
        return town_list
    except BaseException as err:
        logger.critical(f'Searchrequests.search_town: - {err}')
        return 'error'

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
    if response.status_code == 200:
        return [(location.get('gaiaId', '0'), location['regionNames']['displayName']) for location in
                response.json()['sr']]
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
    year_in, month_in, day_in = map(int, godCity.date_arrived.split("-"))
    year_out, month_out, day_out = map(int, godCity.date_leave.split("-"))
    querystring = {"destinationId": {"regionId": destination_id},
                   "checkInDate": {"day": day_in, "month": month_in, "year": year_in},
                   "checkOutDate": {"day": day_out, "month": month_out, "year": year_out},
                   "currency": "EUR",
                   "destination": {"regionId": godCity.id_location},
                   "eapid": 1,
                   "filters": {"availableFilter": "SHOW_AVAILABLE_ONLY"},
                   "locale": "ru_RU",
                   "resultsSize": int(godCity.num_result),
                   "resultsStartingIndex": 0,
                   "rooms": [{"adults": 1}],
                   "siteId": 300000001,
                   "sort": "PRICE_LOW_TO_HIGH",
                   "filters": {
                    "price": {
                        "max": 150,
                        "min": 100
                        }
                    }
                   }
    if price_max and price_min:
        querystring['priceMin'] = f'{price_min}'
        querystring['priceMax'] = f'{price_max}'
    response = requests.request("POST", 'https://hotels4.p.rapidapi.com/properties/v2/list', headers=headers, json=querystring)
    num = 1
    result = []
    data = response.json()
    for hotel in data['data']['propertySearch']['properties']:
        '''Далее функция обрабатывает полученный ответ 
        и формирует результат в виде текстового сообщения 
        с информацией о каждой гостинице, которая подходит 
        по заданным параметрам. 
        В сообщении указываются навзание отеля, количество звезд, 
        адрес, расстояние от центра и цена.'''
        name = hotel['name']
        url_photo = hotel['propertyImage']['image']['url']
        stars = hotel['reviews']['score']
        id = hotel['id']
        distance = int(hotel['destinationInfo']['distanceFromDestination']['value'] * 1.60934)
        price = hotel['mapMarker']['label']
        price_without_dollar = price.replace('$', '')
        if len(godCity.distance):
            if (int(godCity.distance[1]) >= distance >= int(godCity.distance[0])) and (int(godCity.range_prices[1]) >= int(price_without_dollar) >= int(godCity.range_prices[0])):
                godCity.all_hotels = {"name": name, "stars": stars, "url_photo": url_photo, "hotel_id": id, "price": price, "distance":distance}
        else:
            godCity.all_hotels = {"name": name, "stars": stars, "url_photo": url_photo, "hotel_id": id, "price": price, "distance":distance}
        num += 1
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


def show_photos(hotel: 'Hotel', number: int):
    url = "https://hotels4.p.rapidapi.com/properties/v2/detail"
    payload = {
	"currency": "USD",
	"eapid": 1,
	"locale": "en_US",
	"siteId": 300000001,
	"propertyId": hotel['hotel_id']
    }
    hotel['images'] = []

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        for i in range(number):
            hotel['images'].append(data['data']['propertyInfo']['propertyGallery']['images'][i]['image']['url'])
    except BaseException as err:
        logger.critical(f'Searchrequests.show_photo: - {err}')
    return hotel

def set_limits(string: str) -> List:
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
