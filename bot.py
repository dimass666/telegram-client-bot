import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from database import *
import datetime
import threading
import time
import os
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

# ➕ Добавить
@bot.message_handler(func=lambda m: is_authorized(m) and m.text.startswith("➕ Добавить"))
def start_add(message):
    user_states[message.chat.id] = "phone"
    client_data[message.chat.id] = []
    bot.send_message(message.chat.id, "Шаг 1: Введите номер телефона или ник клиента:")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "phone")
def step_birth(message):
    client_data[message.chat.id].append(message.text.strip())
    user_states[message.chat.id] = "birth"
    bot.send_message(message.chat.id, "Шаг 2: Введите дату рождения (дд.мм.гггг):")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "birth")
def step_credentials(message):
    client_data[message.chat.id].append(message.text.strip())
    user_states[message.chat.id] = "credentials"
    bot.send_message(message.chat.id, "Шаг 3: Введите email, пароль аккаунта и пароль от почты (каждое с новой строки):")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "credentials")
def step_subscription_question(message):
    creds = message.text.strip().split('\n')
    if len(creds) < 3:
        return bot.send_message(message.chat.id, "Введите 3 строки: email, пароль аккаунта и пароль почты.")
    client_data[message.chat.id].extend(creds[:3])
    user_states[message.chat.id] = "has_subscription"
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет")
    bot.send_message(message.chat.id, "Шаг 4: Есть ли подписка?", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "has_subscription")
def step_subscription_type(message):
    answer = message.text.strip().lower()
    if answer == "нет":
        client_data[message.chat.id].append("Нету")
        client_data[message.chat.id].append("01.01.2000")
        ask_games_step(message)
    else:
        user_states[message.chat.id] = "subscription_type"
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play")
        bot.send_message(message.chat.id, "Выберите тип подписки:", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "subscription_type")
def step_subscription_duration(message):
    client_data[message.chat.id].append(message.text.strip())
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("1м", "3м", "12м")
    user_states[message.chat.id] = "subscription_duration"
    bot.send_message(message.chat.id, "Выберите срок подписки:", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "subscription_duration")
def step_subscription_region(message):
    client_data[message.chat.id].append(message.text.strip())
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("(тур)", "(укр)", "Другой регион")
    user_states[message.chat.id] = "subscription_region"
    bot.send_message(message.chat.id, "Выберите регион:", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "subscription_region")
def step_subscription_finish(message):
    region = message.text.strip()
    if region.lower() == "другой регион":
        user_states[message.chat.id] = "custom_region"
        return bot.send_message(message.chat.id, "Введите регион вручную (например: (гер)):")
    finish_subscription_step(message, region)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "custom_region")
def handle_custom_region(message):
    region = message.text.strip()
    if not (region.startswith("(") and region.endswith(")")):
        region = f"({region})"
    finish_subscription_step(message, region)

def finish_subscription_step(message, region):
    chat_id = message.chat.id
    name = client_data[chat_id][-2]
    months = client_data[chat_id][-1].replace("м", "")
    sub_string = f"{name} {months}м {region}"
    client_data[chat_id] = client_data[chat_id][:-2]
    client_data[chat_id].append(sub_string)
    user_states[chat_id] = "start_date"
    bot.send_message(chat_id, "Укажите дату начала подписки (дд.мм.гггг):")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "start_date")
def step_games_question(message):
    client_data[message.chat.id].append(message.text.strip())
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет")
    user_states[message.chat.id] = "games_question"
    bot.send_message(message.chat.id, "Есть ли купленные игры?", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "games_question")
def ask_games_step(message):
    if message.text.lower() == "нет":
        client_data[message.chat.id].append("---")
        user_states[message.chat.id] = "codes_question"
        ask_codes(message)
    else:
        user_states[message.chat.id] = "games"
        bot.send_message(message.chat.id, "Введите список игр (каждая с новой строки):")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "games")
def step_codes_question(message):
    client_data[message.chat.id].append("---")
    client_data[message.chat.id].extend(message.text.strip().split('\n'))
    user_states[message.chat.id] = "codes_question"
    ask_codes(message)

def ask_codes(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет")
    bot.send_message(message.chat.id, "Есть ли резервные коды?", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "codes_question")
def handle_codes(message):
    if message.text.lower() == "нет":
        save_client_block(client_data[message.chat.id])
        bot.send_message(message.chat.id, "✅ Клиент добавлен.")
        reset_user_state(message.chat.id)
        show_menu(message)
    else:
        user_states[message.chat.id] = "awaiting_attachment"
        bot.send_message(message.chat.id, "Пришлите скрин или файл с кодами:")

@bot.message_handler(content_types=["photo", "document"])
def receive_attachment(message):
    cid = message.chat.id
    if user_states.get(cid) == "awaiting_attachment":
        phone = client_data[cid][0]
        folder = f"attachments/{phone}"
        os.makedirs(folder, exist_ok=True)
        file = message.photo[-1] if message.photo else message.document
        file_info = bot.get_file(file.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        filename = file_info.file_path.split("/")[-1]
        with open(os.path.join(folder, filename), "wb") as f:
            f.write(downloaded_file)
        save_client_block(client_data[cid])
        bot.send_message(cid, "✅ Клиент добавлен с вложением.")
        reset_user_state(cid)
        show_menu(message)

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "📊 Кол-во по регионам")
def handle_region_stats(message):
    with sqlite3.connect("clients.db") as conn:
        c = conn.cursor()
        c.execute("SELECT type FROM subscriptions")
        subs = c.fetchall()

    if not subs:
        return bot.send_message(message.chat.id, "Подписок нет в базе.")

    tur, ukr, other = 0, 0, 0
    for s in subs:
        stype = s[0].lower()
        if "(тур" in stype:
            tur += 1
        elif "(укр" in stype:
            ukr += 1
        else:
            other += 1

    bot.send_message(
        message.chat.id,
        f"📊 Кол-во подписок:\n"
        f"🇹🇷 Турция: {tur}\n"
        f"🇺🇦 Украина: {ukr}\n"
        f"🌍 Другое: {other}"
    )

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "⬇️ Выгрузить базу")
def export_database(message):
    clients = get_all_clients_text()
    if not clients:
        return bot.send_message(message.chat.id, "Нет клиентов для выгрузки.")
    content = "\n\n".join(clients)
    with io.BytesIO() as output:
        output.write(content.encode("utf-8"))
        output.seek(0)
        bot.send_document(message.chat.id, output, visible_file_name="clients_export.txt", caption="📎 Ваша база клиентов")

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "📋 Список клиентов")
def handle_list_clients(message):
    clients = get_all_clients_text()
    if not clients:
        return bot.send_message(message.chat.id, "Клиентов пока нет.")
    for entry in clients:
        bot.send_message(message.chat.id, entry)

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "🧨 Очистить всю базу")
def confirm_clear(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет")
    bot.send_message(message.chat.id, "⚠️ Вы уверены, что хотите очистить всю базу?", reply_markup=markup)
    user_states[message.chat.id] = "clear_confirm"

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "clear_confirm")
def handle_clear_confirmation(message):
    if message.text.lower() == "да":
        clear_database()
        bot.send_message(message.chat.id, "✅ База полностью очищена.")
    else:
        bot.send_message(message.chat.id, "Очистка отменена.")
    reset_user_state(message.chat.id)
    show_menu(message)

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
