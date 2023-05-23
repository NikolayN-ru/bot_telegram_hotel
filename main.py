import traceback
import requests
import datetime
import telebot
import os
import re
import logging
from request_data import Request
import json
from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE
from api import *
from city import city
from environs import Env


env = Env()
env.read_env()
token = env('TELEGRAM_BOT_TOKEN')

bot = telebot.TeleBot(token)
currency = {'USD': 'долларах', 'RUB': 'рублях', 'EUR': 'евро'}
history_dict = dict()
calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1_callback = CallbackData("calendar_1", "action", "year", "month", "day")
calendar_2_callback = CallbackData("calendar_2", "action", "year", "month", "day")
town_name = ''


def markup_yes_no() -> 'telebot.types.InlineKeyboardMarkup':
    mrk = telebot.types.InlineKeyboardMarkup(row_width=2)
    button1 = telebot.types.InlineKeyboardButton("да", callback_data='1yes1')
    button2 = telebot.types.InlineKeyboardButton("нет", callback_data='2no2')
    mrk.add(button1, button2)
    return mrk


@bot.message_handler(commands=['start'])
def send_welcome(message: 'telebot.types.Message') -> None:
    print(type(message))
    bot.send_message(message.from_user.id, 'Будь как дома, Путник! '
                                           'Сегодня я помогу тебе с поиском ночлега. '
                                           'Чтобы просмотреть доступные функции, нажми /help.')


@bot.message_handler(commands=['help'])
def send_help(message) -> None:
    bot.send_message(message.from_user.id, 'Вот список доступных команд:\n'
                                           '/lowprice - поиск отелей по низким ценам;\n'
                                           '/highprice - поиск отелей по высоким ценам;\n'
                                           '/bestdeal - поиск отелей, подходящих по цене и расположению от центра;\n'
                                           '/history - вывести историю поиска')


@bot.message_handler(commands=['history'])
def send_history(message) -> None:
    path = os.path.abspath(os.path.join('history', 'User' + str(message.from_user.id) + '.txt'))
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as history:
            count = sum(1 for _ in history)
            history.seek(0)
            for i in range(count):
                text = history.readline()
                if text.strip():
                    if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', text):
                        key = str(re.findall(r'\d{2}-\d{2} \d{2}:\d{2}.+', text)[0])
                        history_dict[key] = []
                    else:
                        history_dict[key].append(text)
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
        button_list = list()
        for key in history_dict.keys():
            if history_dict[key]:
                button_list.append(telebot.types.InlineKeyboardButton(text=key, callback_data=key))
        keyboard.add(*button_list)
        bot.send_message(message.from_user.id, "Выбери из списка нужный вам запрос:",
                         reply_markup=keyboard)
    else:
        bot.send_message(message.from_user.id, 'Ты пока еще ничего не искал. '
                                               'Введи команду, или /help для вывода доступных команд')


@bot.message_handler(content_types=['text', 'voice'])
def get_text_messages(message) -> None:
    logger.info(f'User {message.from_user.id} write the message {message.text}')
    if message.text == "Привет":
        bot.send_message(message.from_user.id, "Здравствуй, путник! Для просмотра функций введи /help.")
    elif message.text in ('/lowprice', '/highprice', '/bestdeal'):
        city.clear_hotel_list()
        city.mode_search = message.text
        now = datetime.datetime.now()
        history(f'User' + str(message.from_user.id) + '.txt',
                       f'\n{str(now.strftime("%Y-%m-%d %H:%M"))} - {message.text}. ')
        bot.send_message(message.chat.id, 'В каком городе искать?')
        bot.register_next_step_handler(message, choice_town)
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Повтори или напиши "
                                               "/help для просмотра доступных команд.")


@bot.callback_query_handler(func=lambda call: call.data in history_dict.keys())
def history_show(call) -> None:
    bot.send_message(call.message.chat.id, call.data)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=None)
    if len(history_dict[call.data]) > 0:
        for line in history_dict[call.data]:
            bot.send_message(call.message.chat.id, line)
    bot.send_message(call.message.chat.id, 'Чем я еще могу помочь? (/help для вывода доступных команд)')


def choice_town(message) -> None:
    try:
        bot.send_message(message.from_user.id, 'Обрабатываю запрос, пожалуйста, подожди...')
        list_town = id_search(message.text)
        if not list_town:
            bot.send_message(message.from_user.id, "Город не найден. Проверь название или введи другой город:")
            bot.register_next_step_handler(message, choice_town)
        else:
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
            button_list = list()
            for location in list_town:
                display_name = location[1]

                call_data = '<delimiter>'.join((location[1].split()[0], location[0]))

                button_list.append(telebot.types.InlineKeyboardButton(text=display_name,
                                                                      callback_data=call_data))
            keyboard.add(*button_list)

            bot.send_message(message.from_user.id, "Выбери из списка нужный тебе город:",
                             reply_markup=keyboard)
    except Exception as err_town:
        logger.error(err_town)
        bot.send_message(message.from_user.id, 'Произошла непредвиденная ошибка. Возможно, сервис сейчас недоступен. '
                                               'Пожалуйста, повтори запрос немного позже.')
        city.clear_hotel_list()


@bot.callback_query_handler(func=lambda call: call.data.count('<delimiter>') > 0)
def choose_dates(call) -> None:
    city.name_town, city.id_location = call.data.split('<delimiter>')
    history(f'User' + str(call.message.chat.id) + '.txt', f'{city.name_town}')
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    bot.send_message(call.message.chat.id, f'Выбран город: {city.name_town}')
    now = datetime.datetime.now()
    bot.send_message(call.message.chat.id, f"Выбери дату ЗАЕЗДА:",
                     reply_markup=calendar.create_calendar(name=calendar_1_callback.prefix,
                                                           year=now.year, month=now.month))


@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_1_callback.prefix))
def date_arrived(call: telebot.types.CallbackQuery) -> None:
    name, action, year, month, day = call.data.split(calendar_1_callback.sep)
    date = calendar.calendar_query_handler(bot=bot, call=call, name=name, action=action,
                                           year=year, month=month, day=day)
    if action == "DAY":
        city.date_arrived = date.strftime('%Y-%m-%d')
        now = datetime.datetime.now()
        if city.date_arrived < now.strftime('%Y-%m-%d'):
            bot.send_message(call.message.chat.id, "Ошибка при выборе даты заезда. Следует указывать дату, "
                                                   "не раньше сегодняшней.",
                             reply_markup=calendar.create_calendar(name=calendar_1_callback.prefix,
                                                                   year=now.year, month=now.month))
        else:
            bot.send_message(call.message.chat.id, f'Дата заезда: {city.date_arrived}. Выбери дату ВЫЕЗДА:',
                             reply_markup=calendar.create_calendar(name=calendar_2_callback.prefix,
                                                                   year=now.year, month=now.month))
    elif action == "CANCEL":
        bot.send_message(call.message.chat.id, 'Запрос был отменен. Введи /help для вывода доступных команд')
        city.clear_hotel_list()


@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_2_callback.prefix))
def date_leave(call: telebot.types.CallbackQuery) -> None:
    name, action, year, month, day = call.data.split(calendar_2_callback.sep)
    date = calendar.calendar_query_handler(bot=bot, call=call, name=name, action=action,
                                           year=year, month=month, day=day)
    if action == "DAY":
        now = datetime.datetime.now()
        city.date_leave = date.strftime('%Y-%m-%d')
        if city.date_leave <= city.date_arrived:
            bot.send_message(call.message.chat.id, f"Ошибка при выборе дат. Дата выезда должна быть позже даты заезда. "
                                                   f"({city.date_arrived})",
                             reply_markup=calendar.create_calendar(name=calendar_2_callback.prefix,
                                                                   year=now.year, month=now.month))
        else:
            bot.send_message(call.message.chat.id,
                             f'Дата заезда: {city.date_arrived}, дата выезда: {city.date_leave}.'
                             f'\nСколько отелей показать? (не более 25)')
            bot.register_next_step_handler(call.message, choice_currency)
    elif action == "CANCEL":
        bot.send_message(call.message.chat.id, 'Запрос был отменен. Введи /help для вывода доступных команд.')
        city.clear_hotel_list()


def choice_currency(message) -> None:
    try:
        if int(message.text):
            city.num_result = message.text
            keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1)
            button_list = list()
            for item in currency.keys():
                button_list.append(telebot.types.KeyboardButton(text=item))
            keyboard.add(*button_list)
            bot.send_message(message.from_user.id, "Выбери валюту:",
                             reply_markup=keyboard)
            if city.mode_search == 'DISTANCE_FROM_LANDMARK':
                bot.register_next_step_handler(message, input_prices)
            else:
                bot.register_next_step_handler(message, show_results)
    except ValueError as error:
        logger.error(f'From User {message.from_user.id}: {message.text} - {error}')
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Введи пожалуйста число:")
        bot.register_next_step_handler(message, choice_currency)


def input_prices(message) -> None:
    try:
        if message.text not in currency.keys():
            logger.error(f'From User {message.from_user.id}: {message.text} - {ValueError}')
            bot.send_message(message.from_user.id, "Неверная валюта. Тебе необходимо выбрать валюту из списка ниже!")
            bot.register_next_step_handler(message, input_prices)
        else:
            city.currency = message.text
            bot.send_message(message.from_user.id, f'Введи диапазон цен через пробел в {currency[city.currency]}:',
                             reply_markup=telebot.types.ReplyKeyboardRemove())
            bot.register_next_step_handler(message, input_distance)
    except Exception as error:
        logger.critical(f'From User {message.from_user.id}: {message.text} - {error}')
        bot.send_message(message.from_user.id, "Непредвиденная ошибка. Повтори запрос сначала.")
        city.clear_hotel_list()


def input_distance(message) -> None:
    try:
        prices_limit = set_limits(message.text)
        if prices_limit:
            city.range_prices = prices_limit
            bot.send_message(message.from_user.id, 'Введи диапазон расстояния до центра в километрах:')
            bot.register_next_step_handler(message, show_results)
        else:
            bot.send_message(message.from_user.id, f'Я тебя не понимаю. '
                                                   f'Необходимо ввести две суммы в {currency[city.currency]}:')
            logger.error(f'From User {message.from_user.id}: {message.text} - {ValueError}')
            bot.register_next_step_handler(message, input_distance)
    except Exception as error:
        logger.critical(f'From User {message.from_user.id}: {message.text} - {error}')
        bot.send_message(message.from_user.id, "Непредвиденная ошибка. Повтори запрос сначала.")


def show_results(message) -> None:
    if city.mode_search == 'DISTANCE_FROM_LANDMARK':
        distance_limit = set_limits(message.text.replace(',', '.'))

        if distance_limit:
            bot.send_message(message.from_user.id, 'Обрабатываю запрос, пожалуйста, подожди...')
            best_deal(city, distance_limit)
        else:
            logger.error(f'From User {message.from_user.id}: {message.text} - {ValueError}')
            bot.send_message(message.from_user.id, f'Я тебя не понимаю. '
                                                   f'Необходимо ввести два числа в километрах!')
            bot.register_next_step_handler(message, show_results)
    else:
        if message.text not in currency.keys():
            distance_limit = False
            bot.send_message(message.from_user.id, "Неверная валюта. Тебе необходимо выбрать валюту из списка ниже!")
            bot.register_next_step_handler(message, show_results)
        else:
            distance_limit = True
            keyboard = telebot.types.ReplyKeyboardRemove()
            city.currency = message.text
            bot.send_message(message.from_user.id, 'Обрабатываю запрос, пожалуйста, подожди...',
                             reply_markup=keyboard)
            print('meow', city.name_town)
            get_hotels(Request, city.name_town)
            print('meow1', get_hotels(Request, city.name_town))

            #сюда код доходит, но тут ошибка с параметрами для get_hotels
    if distance_limit:
        if len(city.all_hotels) == 0:
            logger.info('Nothing found for request')
            bot.send_message(message.from_user.id, 'Извини, по запрашиваемым параметрам ничего не найдено.'
                                                   'Попробуй повторить запрос и изменить параметры поиска.')
            history(f'User' + str(message.from_user.id) + '.txt', '\nНичего не найдено.')
        else:
            n = 1
            logger.info('Request was already successful')
            for hotel in city.all_hotels:
                bot.send_message(message.from_user.id, ''.join([str(n), '. ', str(hotel)]))
                history(f'User' + str(message.from_user.id) + '.txt', ''.join(['\n', str(n), '. ', str(hotel)]))
                n += 1
            else:
                bot.send_message(message.from_user.id, 'Хотешь взглянуть на фотографии отелей?',
                                 reply_markup=markup_yes_no())


@bot.callback_query_handler(func=lambda call: call.data in ('1yes1', '2no2'))
def photo_hotels(call) -> None:
    if call.data == '1yes1':
        bot.send_message(call.message.chat.id, 'Сколько фотографий показать? (не больше 7')
        bot.register_next_step_handler(call.message, number_of_photos)
    elif call.data == '2no2':
        bot.send_message(call.message.chat.id, 'Чем я еще могу тебе помочь? (/help для вывода доступных команд.)')
        city.clear_hotel_list()
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=None)


def number_of_photos(message) -> None:
    if message.text.isdigit():
        if int(message.text) not in range(1, 8):
            bot.send_message(message.from_user.id,
                             'Я могу показать тебе не более 7 фотографий. Введи число от 1 до 7.')
            bot.register_next_step_handler(message, number_of_photos)
        else:
            city.num_result = int(message.text)
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
            button_list = list()
            for item in city.all_hotels:
                button_list.append(telebot.types.InlineKeyboardButton(text=str(item.name),
                                                    callback_data='<ph0t0>'.join(str([city.all_hotels.index(item)]))))
            keyboard.add(*button_list)
            bot.send_message(message.from_user.id, "Фотографии какого отеля показать?:",
                             reply_markup=keyboard)
    else:
        bot.send_message(message.from_user.id, 'Я тебя не понимаю. Необходимо ввести число от 1 до 7!')
        bot.register_next_step_handler(message, number_of_photos)


@bot.callback_query_handler(func=lambda call: call.data.count('<ph0t0>') > 0)
def show_photo(call) -> None:
    index = int(call.data.split('<ph0t0>')[1])
    bot.send_message(call.message.chat.id, city.all_hotels[index].name)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=None)
    try:
        bot.send_message(call.message.chat.id, 'Загружаю фотографии, пожалуйста, подожди...')
        show_photos(city.all_hotels[index], city.num_result)
        for item in city.all_hotels[index].url_photo:
            file = requests.get(item)
            img = 'img.jpg'
            with open(img, 'wb') as f:
                f.write(file.content)
            with open('img.jpg', 'rb') as img:
                bot.send_photo(call.message.chat.id, img, f'{city.all_hotels[index].name}')
            os.remove('img.jpg')
        else:
            bot.send_message(call.message.chat.id, 'Хочешь посмотреть фотографии по другому отелю?',
                             reply_markup=markup_yes_no())
    except Exception as photo_err:
        logger.error(photo_err)
        bot.send_message(call.message.chat.id, "Фотографий по данному отелю не найдено. "
                                               "Хотишь посмотреть фотографии по другому отелю?",
                                               reply_markup=markup_yes_no())


if __name__ == "__main__":
    bot.polling(none_stop=True, interval=0)