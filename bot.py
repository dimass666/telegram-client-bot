import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database import *
import datetime
import threading
import time
import os

API_TOKEN = "7832902735:AAGJzhg00l7x2R8jr-eonf5KZF9c8QYQaCY"
ALLOWED_USER_ID = 350902460

bot = telebot.TeleBot(API_TOKEN)

def is_authorized(message):
    return message.from_user.id == ALLOWED_USER_ID

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
    markup.add(KeyboardButton("⬇️ Выгрузить базу"))
    bot.send_message(message.chat.id, "Меню команд", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and m.text.startswith('+7'))
def handle_phone_or_block(message):
    lines = message.text.strip().split('\n')
    if len(lines) >= 5:
        phone = lines[0]
        save_client_block(lines)
        bot.reply_to(message, f"✅ Клиент {phone} добавлен.")
    else:
        client = get_client_block(message.text.strip())
        if client:
            bot.send_message(message.chat.id, client)
        else:
            bot.send_message(message.chat.id, "Клиент не найден.")

@bot.message_handler(content_types=['photo', 'document'])
def handle_attachments(message):
    if not is_authorized(message) or not message.reply_to_message:
        return
    phone = message.reply_to_message.text.strip().split('\n')[0]
    folder = f"attachments/{phone}"
    os.makedirs(folder, exist_ok=True)
    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(f"{folder}/{file_id}.jpg", 'wb') as f:
            f.write(downloaded_file)
    elif message.content_type == 'document':
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(f"{folder}/{message.document.file_name}", 'wb') as f:
            f.write(downloaded_file)
    bot.reply_to(message, f"Файл сохранён для клиента {phone}.")

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "⬇️ Выгрузить базу")
def send_database(message):
    with open("clients_encrypted.db", "rb") as f:
        bot.send_document(message.chat.id, f)

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "📋 Список клиентов")
def list_clients(message):
    clients = get_all_clients()
    text = "\n".join(clients)
    bot.send_message(message.chat.id, text if text else "Клиенты не найдены.")

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "📊 Кол-во по регионам")
def region_stats(message):
    stats = get_region_stats()
    text = "\n".join([f"{region}: {count}" for region, count in stats.items()])
    bot.send_message(message.chat.id, text)

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
                    msg = f"Сегодня день рождения у клиента:\n{phone} ({birthday})"
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("Открыть данные клиента", callback_data=f"open_client_{phone}"))
                    bot.send_message(ALLOWED_USER_ID, msg, reply_markup=markup)
        time.sleep(3600)

init_db()
threading.Thread(target=notify_loop, daemon=True).start()
bot.infinity_polling()