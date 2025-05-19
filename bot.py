import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import *
import datetime
import threading
import time
import os
import sqlite3

API_TOKEN = "7832902735:AAGJzhg00l7x2R8jr-eonf5KZF9c8QYQaCY"
ALLOWED_USER_ID = 350902460

bot = telebot.TeleBot(API_TOKEN)
user_states = {}
client_data = {}

ADD_CLIENT_STEPS = [
    "phone", "birth", "credentials", "ask_subscription", "subscription", "start_date", "games"
]

def is_authorized(message):
    return message.from_user.id == ALLOWED_USER_ID

def reset_user_state(user_id):
    user_states.pop(user_id, None)
    client_data.pop(user_id, None)

@bot.message_handler(commands=['start'])
def start(message):
    if not is_authorized(message):
        return bot.reply_to(message, "У тебя нет доступа к этому боту.")
    show_menu(message)

@bot.message_handler(commands=['menu'])
def show_menu(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("➕ Добавить"), KeyboardButton("✏️ Редактировать"))
    markup.add(KeyboardButton("🔍 Найти клиента"), KeyboardButton("🗑 Удалить"))
    markup.add(KeyboardButton("📋 Список клиентов"), KeyboardButton("📊 Кол-во по регионам"))
    markup.add(KeyboardButton("⬇️ Выгрузить базу"), KeyboardButton("🧨 Очистить всю базу"))
    bot.send_message(message.chat.id, "Меню команд", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "➕ Добавить")
def start_add_client(message):
    user_states[message.chat.id] = "phone"
    client_data[message.chat.id] = []
    bot.send_message(message.chat.id, "Шаг 1/6: Введите номер телефона или Telegram ник клиента:")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "ask_subscription")
def handle_subscription_check(message):
    answer = message.text.strip().lower()
    if answer == "да":
        user_states[message.chat.id] = "subscription"
        bot.send_message(message.chat.id, "Шаг 4/6: Введите название подписки, срок и регион (например: PS Plus Extra 3м (тур)):")
    elif answer == "нет":
        client_data[message.chat.id].append("Нету")
        client_data[message.chat.id].append("01.01.2000")
        user_states[message.chat.id] = "games"
        bot.send_message(message.chat.id, "Шаг 5/6: Укажите игры (каждая с новой строки):")
    else:
        bot.send_message(message.chat.id, "Ответьте 'Да' или 'Нет': Есть ли подписка?")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) in ADD_CLIENT_STEPS)
def handle_add_steps(message):
    state = user_states[message.chat.id]
    value = message.text.strip()

    if state == "phone":
        client_data[message.chat.id].append(value)
        user_states[message.chat.id] = "birth"
        bot.send_message(message.chat.id, "Шаг 2/6: Введите дату рождения (дд.мм.гггг):")
    elif state == "birth":
        client_data[message.chat.id].append(value)
        user_states[message.chat.id] = "credentials"
        bot.send_message(message.chat.id, "Шаг 3/6: Введите email, пароль аккаунта, пароль от почты (каждое на новой строке):")
    elif state == "credentials":
        creds = value.split('\n')
        if len(creds) < 3:
            bot.send_message(message.chat.id, "Введите 3 строки: email, пароль, пароль почты.")
            return
        client_data[message.chat.id].extend(creds[:3])
        user_states[message.chat.id] = "ask_subscription"
        bot.send_message(message.chat.id, "Есть ли у клиента подписка? (Да / Нет)")
    elif state == "subscription":
        client_data[message.chat.id].append(value)
        user_states[message.chat.id] = "start_date"
        bot.send_message(message.chat.id, "Шаг 5/6: Укажите дату начала подписки (дд.мм.гггг):")
    elif state == "start_date":
        client_data[message.chat.id].append(value)
        user_states[message.chat.id] = "games"
        bot.send_message(message.chat.id, "Шаг 6/6: Укажите игры (каждая с новой строки):")
    elif state == "games":
        games = value.split('\n')
        client_data[message.chat.id].append("---")
        client_data[message.chat.id].extend(games)
        save_client_block(client_data[message.chat.id])
        bot.send_message(message.chat.id, f"✅ Клиент {client_data[message.chat.id][0]} добавлен.")
        reset_user_state(message.chat.id)

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "🔍 Найти клиента")
def start_search_client(message):
    user_states[message.chat.id] = "search_client"
    bot.send_message(message.chat.id, "Введите номер телефона или ник клиента для поиска:")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "search_client")
def process_search_client(message):
    query = message.text.strip()
    client = get_client_block(query)
    if client:
        bot.send_message(message.chat.id, f"Найден клиент:\n{client}")
    else:
        bot.send_message(message.chat.id, "Клиент не найден.")
    reset_user_state(message.chat.id)

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "📋 Список клиентов")
def handle_list_clients(message):
    with sqlite3.connect("clients.db") as conn:
        c = conn.cursor()
        c.execute("SELECT phone FROM clients")
        phones = [row[0] for row in c.fetchall()]
        if not phones:
            bot.send_message(message.chat.id, "База пуста.")
            return
        for phone in phones:
            data = get_client_block(phone)
            bot.send_message(message.chat.id, data)

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "📊 Кол-во по регионам")
def handle_region_stats(message):
    with sqlite3.connect("clients.db") as conn:
        c = conn.cursor()
        c.execute("SELECT type FROM subscriptions")
        regions = {"тур": 0, "укр": 0, "другое": 0}
        for (sub_type,) in c.fetchall():
            if "тур" in sub_type.lower():
                regions["тур"] += 1
            elif "укр" in sub_type.lower():
                regions["укр"] += 1
            else:
                regions["другое"] += 1
        stats = (
            f"Подписки по регионам:\n"
            f"Турция: {regions['тур']}\n"
            f"Украина: {regions['укр']}\n"
            f"Другое: {regions['другое']}"
        )
        bot.send_message(message.chat.id, stats)

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "🧨 Очистить всю базу")
def confirm_clear_database(message):
    user_states[message.chat.id] = "confirm_clear_db"
    bot.send_message(message.chat.id, "Вы уверены, что хотите удалить всю базу? (Да / Нет)")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "confirm_clear_db")
def clear_database_action(message):
    if message.text.strip().lower() == "да":
        with sqlite3.connect("clients.db") as conn:
            c = conn.cursor()
            c.execute("DELETE FROM clients")
            c.execute("DELETE FROM subscriptions")
            c.execute("DELETE FROM games")
            conn.commit()
        bot.send_message(message.chat.id, "✅ Вся база очищена.")
    else:
        bot.send_message(message.chat.id, "Операция отменена.")
    reset_user_state(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("open_client_"))
def handle_open_client(call):
    phone = call.data.replace("open_client_", "")
    client = get_client_block(phone)
    if client:
        bot.send_message(call.message.chat.id, client)
    else:
        bot.send_message(call.message.chat.id, "Клиент не найден.")

def notify_loop():
    while True:
        now = datetime.datetime.now()
        if now.hour == 9:
            items = get_upcoming_notifications()
            for notif in items:
                phone, typ, months, end_date, birthday = notif
                if end_date:
                    msg = f"Напоминание:\nУ клиента {phone} заканчивается подписка {typ} ({months}м) завтра ({end_date})"
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("Открыть данные клиента", callback_data=f"open_client_{phone}"))
                    bot.send_message(ALLOWED_USER_ID, msg, reply_markup=markup)
                if birthday:
                    msg = f"У клиента сегодня день рождения:\n"
                    bot.send_message(ALLOWED_USER_ID, msg)
                    data = get_client_block(phone)
                    if data:
                        bot.send_message(ALLOWED_USER_ID, data)
        time.sleep(3600)

init_db()
threading.Thread(target=notify_loop, daemon=True).start()
bot.infinity_polling()