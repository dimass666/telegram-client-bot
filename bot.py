import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from database import *
import datetime
import threading
import time
import os
import sqlite3

API_TOKEN = "ТВОЙ_ТОКЕН"
ALLOWED_USER_ID = 350902460

bot = telebot.TeleBot(API_TOKEN)
user_states = {}
client_data = {}

def is_authorized(message):
    return message.from_user.id == ALLOWED_USER_ID

def reset_user_state(user_id):
    user_states.pop(user_id, None)
    client_data.pop(user_id, None)

@bot.message_handler(commands=['start'])
def start(message):
    if not is_authorized(message):
        return bot.reply_to(message, "У тебя нет доступа к этому боту.")
    bot.send_message(message.chat.id, "👋 Добро пожаловать! Выберите действие из меню ниже.")
    show_menu(message)

@bot.message_handler(commands=['menu'])
def show_menu(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Добавить", "✏️ Редактировать")
    markup.add("🔍 Найти клиента", "🗑 Удалить")
    markup.add("📋 Список клиентов", "📊 Кол-во по регионам")
    markup.add("⬇️ Выгрузить базу", "🧨 Очистить всю базу")
    markup.add("🚀 Старт")
    bot.send_message(message.chat.id, "📋 Главное меню:", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "🚀 Старт")
def start_button(message):
    start(message)

# Здесь дальше идут все остальные функции добавления клиента, подписки, напоминаний и т.д.
# Чтобы сохранить краткость, они могут быть восстановлены на основе предыдущей логики

def notify_loop():
    while True:
        now = datetime.datetime.now()
        if now.hour == 9:
            for phone, typ, months, end, bday in get_upcoming_notifications():
                if end:
                    msg = f"Напоминание:\nУ клиента {phone} заканчивается подписка {typ} ({months}м) завтра ({end})"
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("Открыть данные клиента", callback_data=f"open_client_{phone}"))
                    bot.send_message(ALLOWED_USER_ID, msg, reply_markup=markup)
                if bday:
                    bot.send_message(ALLOWED_USER_ID, f"У клиента сегодня день рождения:\n{phone}")
                    data = get_client_block(phone)
                    if data:
                        bot.send_message(ALLOWED_USER_ID, data)
        time.sleep(3600)

init_db()
threading.Thread(target=notify_loop, daemon=True).start()
bot.infinity_polling()
