import os
import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from database import *
import datetime
import threading
import time
import io
import sqlite3

API_TOKEN = "7832902735:AAGJzhg00l7x2R8jr-eonf5KZF9c8QYQaCY"
ALLOWED_USER_ID = 350902460

bot = telebot.TeleBot(API_TOKEN)
user_states = {}
client_data = {}

def is_authorized(message):
    return message.from_user.id == ALLOWED_USER_ID

def reset_user_state(user_id):
    user_states.pop(user_id, None)
    client_data.pop(user_id, None)

def show_menu(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Добавить", "✏️ Редактировать")
    markup.add("🔍 Найти клиента")
    markup.add("📋 Список клиентов", "📊 Кол-во по регионам")
    markup.add("⬇️ Выгрузить базу", "🧨 Очистить всю базу")
    bot.send_message(message.chat.id, "Меню команд", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("open_client_"))
def handle_callback(call):
    phone = call.data.split("open_client_")[1]
    data = get_client_block(phone)
    if data:
        bot.send_message(call.message.chat.id, data)
    else:
        bot.send_message(call.message.chat.id, "Данные клиента не найдены.")

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
                    bot.send_message(ALLOWED_USER_ID, f"🎉 У клиента сегодня день рождения:\n{phone}")
                    data = get_client_block(phone)
                    if data:
                        bot.send_message(ALLOWED_USER_ID, data)
        time.sleep(3600)

init_db()
threading.Thread(target=notify_loop, daemon=True).start()
bot.infinity_polling()
