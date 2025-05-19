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

ADD_CLIENT_STEPS = [
    "phone", "birth", "credentials", "has_subscription",
    "subscription_type", "subscription_duration", "subscription_region",
    "start_date", "games"
]

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "➕ Добавить")
def start_add_client(message):
    user_states[message.chat.id] = "phone"
    client_data[message.chat.id] = []
    bot.send_message(message.chat.id, "Шаг 1: Введите номер телефона или Telegram ник клиента:")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "ask_games")
def handle_ask_games(message):
    cid = message.chat.id
    choice = message.text.strip().lower()
    if "не куплены" in choice:
        user_states[cid] = "ask_attachment"
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("Да"), KeyboardButton("Нет"))
        bot.send_message(cid, "Есть ли резервные коды?", reply_markup=markup)
    elif "куплены" in choice:
        user_states[cid] = "games"
        bot.send_message(cid, "Введите список игр (каждая с новой строки):")
    else:
        bot.send_message(cid, "Пожалуйста, выбери: Игры не куплены / Игры куплены.")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "ask_attachment")
def handle_attachment_question(message):
    cid = message.chat.id
    answer = message.text.strip().lower()
    if answer == "да":
        user_states[cid] = "awaiting_attachment"
        bot.send_message(cid, "Пришли скриншот или документ с резервными кодами:")
    elif answer == "нет":
        save_client_block(client_data[cid])
        bot.send_message(cid, f"✅ Клиент {client_data[cid][0]} добавлен.")
        reset_user_state(cid)
    else:
        bot.send_message(cid, "Выберите 'Да' или 'Нет'.")

@bot.message_handler(content_types=['document', 'photo'])
def handle_attachments(message):
    cid = message.chat.id
    if user_states.get(cid) == "awaiting_attachment":
        client_id = client_data[cid][0]
        folder = f"attachments/{client_id}"
        os.makedirs(folder, exist_ok=True)
        file_id = message.document.file_id if message.document else message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        filename = file_info.file_path.split("/")[-1]
        filepath = os.path.join(folder, filename)
        with open(filepath, 'wb') as f:
            f.write(downloaded_file)
        save_client_block(client_data[cid])
        bot.send_message(cid, f"✅ Клиент {client_id} добавлен с вложением.")
        reset_user_state(cid)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) in ADD_CLIENT_STEPS)
def handle_add_steps(message):
    cid = message.chat.id
    state = user_states[cid]
    value = message.text.strip()

    if state == "phone":
        client_data[cid].append(value)
        user_states[cid] = "birth"
        bot.send_message(cid, "Шаг 2: Введите дату рождения (дд.мм.гггг):")
    elif state == "birth":
        client_data[cid].append(value)
        user_states[cid] = "credentials"
        bot.send_message(cid, "Шаг 3: Введите email, пароль аккаунта, пароль от почты (каждое с новой строки):")
    elif state == "credentials":
        creds = value.split('\n')
        if len(creds) < 3:
            bot.send_message(cid, "Введите 3 строки: email, пароль аккаунта, пароль почты.")
            return
        client_data[cid].extend(creds[:3])
        user_states[cid] = "has_subscription"
        bot.send_message(cid, "Шаг 4: Есть ли у клиента подписка? (Да / Нет)")
    elif state == "has_subscription":
        if value.lower() == "да":
            user_states[cid] = "subscription_type"
            bot.send_message(cid, "Укажите название подписки (например: PS Plus Deluxe):")
        else:
            client_data[cid].append("Нету")
            client_data[cid].append("01.01.2000")
            user_states[cid] = "ask_games"
            markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add(KeyboardButton("Игры не куплены"), KeyboardButton("Игры куплены"))
            bot.send_message(cid, "Шаг 6: У клиента есть купленные игры?", reply_markup=markup)
    elif state == "subscription_type":
        client_data[cid].append(value)
        user_states[cid] = "subscription_duration"
        bot.send_message(cid, "Укажите срок подписки (в месяцах, например: 3):")
    elif state == "subscription_duration":
        client_data[cid].append(value)
        user_states[cid] = "subscription_region"
        bot.send_message(cid, "Укажите регион (например: (тур) или (укр)):")
    elif state == "subscription_region":
        region = value if value.startswith("(") and value.endswith(")") else f"({value})"
        name = client_data[cid][-2]
        months = client_data[cid][-1]
        sub_string = f"{name} {months}м {region}"
        client_data[cid] = client_data[cid][:-2]
        client_data[cid].append(sub_string)
        user_states[cid] = "start_date"
        bot.send_message(cid, "Шаг 5: Укажите дату начала подписки (дд.мм.гггг):")
    elif state == "start_date":
        client_data[cid].append(value)
        user_states[cid] = "ask_games"
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("Игры не куплены"), KeyboardButton("Игры куплены"))
        bot.send_message(cid, "Шаг 6: У клиента есть купленные игры?", reply_markup=markup)
    elif state == "games":
        client_data[cid].append("---")
        client_data[cid].extend(value.split('\n'))
        user_states[cid] = "ask_attachment"
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("Да"), KeyboardButton("Нет"))
        bot.send_message(cid, "Есть ли резервные коды?", reply_markup=markup)

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