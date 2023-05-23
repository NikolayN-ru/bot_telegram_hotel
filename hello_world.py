import telebot
from environs import Env

env = Env()
env.read_env()
token = env('TELEGRAM_BOT_TOKEN')

bot = telebot.TeleBot(token)


@bot.message_handler(commands=['start'])
def welcome_start(message):
    bot.send_message(message.chat.id, 'Напиши "Привет" или "/hello_world"')


@bot.message_handler(commands=['hello_world'])
def hello(message):
    bot.send_message(message.chat.id, 'Здравствуй, Путник!')


@bot.message_handler(content_types=['text'])
def text(message):
    if message.text == 'Привет':
        bot.send_message(message.chat.id, 'Здравствуй, Путник!')


bot.polling()