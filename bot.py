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

@bot.message_handler(commands=['start'])
def start(message):
    if not is_authorized(message):
        return bot.reply_to(message, "У тебя нет доступа к этому боту.")
    show_menu(message)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "edit_menu")
def handle_edit_choice(message):
    phone = client_data.get(message.chat.id)
    if not phone:
        return
    choice = message.text
    if choice == "📱 Телефон":
        user_states[message.chat.id] = "edit_phone"
        bot.send_message(message.chat.id, "Введите новый номер телефона:")
    elif choice == "📅 Дата рождения":
        user_states[message.chat.id] = "edit_birth"
        bot.send_message(message.chat.id, "Введите новую дату рождения (дд.мм.гггг):")
    elif choice == "🔐 Аккаунт":
        user_states[message.chat.id] = "edit_account"
        bot.send_message(message.chat.id, "Введите email, пароль аккаунта и пароль почты (с новой строки):")
    elif choice == "🕹 Подписка":
        user_states[message.chat.id] = "edit_subscription_type"
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play")
        bot.send_message(message.chat.id, "Выберите новый тип подписки:", reply_markup=markup)
    elif choice == "🎮 Игры":
        user_states[message.chat.id] = "edit_games"
        bot.send_message(message.chat.id, "Введите новый список игр (каждая с новой строки):")
    elif choice == "📎 Резервные коды":
        user_states[message.chat.id] = "edit_attachment"
        bot.send_message(message.chat.id, "Пришлите новый файл или фото:")
    elif choice == "❌ Отмена":
        reset_user_state(message.chat.id)
        show_menu(message)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "edit_subscription_type")
def edit_sub_duration(message):
    client_data[message.chat.id] = [message.text.strip()]
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("1м", "3м", "12м")
    user_states[message.chat.id] = "edit_subscription_duration"
    bot.send_message(message.chat.id, "Выберите новый срок подписки:", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "edit_subscription_duration")
def edit_sub_region(message):
    client_data[message.chat.id].append(message.text.strip())
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("(тур)", "(укр)", "Другой регион")
    user_states[message.chat.id] = "edit_subscription_region"
    bot.send_message(message.chat.id, "Выберите регион:", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "edit_subscription_region")
def edit_sub_region_value(message):
    region = message.text.strip()
    if region.lower() == "другой регион":
        user_states[message.chat.id] = "edit_subscription_custom_region"
        return bot.send_message(message.chat.id, "Введите регион вручную (например: (гер)):")
    finish_subscription_edit(message, region)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "edit_subscription_custom_region")
def edit_sub_custom_region(message):
    region = message.text.strip()
    if not (region.startswith("(") and region.endswith(")")):
        region = f"({region})"
    finish_subscription_edit(message, region)

def finish_subscription_edit(message, region):
    chat_id = message.chat.id
    phone = client_data.get(chat_id)
    type_, duration = client_data[chat_id][:2]
    user_states[chat_id] = "edit_subscription_date"
    client_data[chat_id] = [type_, duration, region]
    bot.send_message(chat_id, "Введите новую дату начала подписки (дд.мм.гггг):")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "edit_subscription_date")
def update_subscription(message):
    phone = client_data[message.chat.id]
    type_, duration, region = client_data[message.chat.id][:3]
    start_date = message.text.strip()
    months = int(duration.replace("м", ""))
    start = datetime.datetime.strptime(start_date, "%d.%m.%Y")
    end = start + datetime.timedelta(days=30 * months)
    full_type = f"{type_} {duration} {region}"
    with sqlite3.connect("clients.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM subscriptions WHERE phone = ?", (phone,))
        c.execute("INSERT INTO subscriptions VALUES (?, ?, ?, ?, ?)", (phone, full_type, months, start_date, end.strftime("%d.%m.%Y")))
        conn.commit()
    bot.send_message(message.chat.id, "Подписка обновлена.")
    show_menu(message)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "edit_games")
def update_games(message):
    phone = client_data.get(message.chat.id)
    games = message.text.strip().split("\n")
    with sqlite3.connect("clients.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM games WHERE phone = ?", (phone,))
        for g in games:
            c.execute("INSERT INTO games VALUES (?, ?)", (phone, g))
        conn.commit()
    bot.send_message(message.chat.id, "Список игр обновлён.")
    show_menu(message)

@bot.message_handler(content_types=["photo", "document"])
def update_attachment_edit(message):
    if user_states.get(message.chat.id) != "edit_attachment":
        return
    phone = client_data.get(message.chat.id)
    if not phone:
        return
    folder = f"attachments/{phone}"
    os.makedirs(folder, exist_ok=True)
    file = message.photo[-1] if message.photo else message.document
    file_info = bot.get_file(file.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    filename = file_info.file_path.split("/")[-1]
    with open(os.path.join(folder, filename), "wb") as f:
        f.write(downloaded_file)
    bot.send_message(message.chat.id, "Вложение обновлено.")
    reset_user_state(message.chat.id)
    show_menu(message)

init_db()
threading.Thread(target=notify_loop, daemon=True).start()
bot.infinity_polling()
