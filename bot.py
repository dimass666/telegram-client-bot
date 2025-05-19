import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import init_db, save_client_block, get_client_block, get_upcoming_notifications
import datetime
import threading
import time

# Твой токен и Telegram ID
API_TOKEN = "7832902735:AAGJzhg00l7x2R8jr-eonf5KZF9c8QYQaCY"
ALLOWED_USER_ID = 350902460

bot = telebot.TeleBot(API_TOKEN)

def is_authorized(message):
    return message.from_user.id == ALLOWED_USER_ID

@bot.message_handler(commands=['start'])
def start(message):
    if not is_authorized(message):
        return bot.reply_to(message, "У тебя нет доступа к этому боту.")
    bot.send_message(message.chat.id, "Бот запущен. Отправь номер клиента или блок данных для добавления/обновления.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('+7'))
def handle_phone_or_block(message):
    if not is_authorized(message):
        return
    lines = message.text.strip().split('\n')
    if len(lines) >= 5:
        phone = lines[0]
        save_client_block(lines)
        bot.reply_to(message, f"Клиент {phone} сохранён/обновлён.")
    else:
        client = get_client_block(message.text.strip())
        if client:
            bot.send_message(message.chat.id, client)
        else:
            bot.send_message(message.chat.id, "Клиент не найден.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("open_client_"))
def handle_open_client(call):
    if call.from_user.id != ALLOWED_USER_ID:
        return
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

# Запуск
init_db()
threading.Thread(target=notify_loop, daemon=True).start()
bot.infinity_polling()