import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from database import *
import datetime
import threading
import time
import os

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

# ✏️ Редактировать
@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "✏️ Редактировать")
def edit_client_start(message):
    bot.send_message(message.chat.id, "Введите номер телефона или ник клиента для редактирования:")
    user_states[message.chat.id] = "edit_request"

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "edit_request")
def handle_edit_request(message):
    phone = message.text.strip()
    data = get_client_block(phone)
    if not data:
        bot.send_message(message.chat.id, "Клиент не найден.")
        reset_user_state(message.chat.id)
        return show_menu(message)
    client_data[message.chat.id] = phone
    user_states[message.chat.id] = "edit_menu"
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("📱 Телефон", "📅 Дата рождения")
    markup.add("🔐 Аккаунт", "🕹 Подписка")
    markup.add("🎮 Игры", "📎 Резервные коды")
    markup.add("🗑 Удалить клиента", "❌ Отмена")
    bot.send_message(message.chat.id, f"Данные клиента:\n{data}", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "edit_menu")
def edit_menu_choice(message):
    choice = message.text.strip()
    if choice == "❌ Отмена":
        bot.send_message(message.chat.id, "Редактирование отменено.")
        reset_user_state(message.chat.id)
        return show_menu(message)
    elif choice == "🗑 Удалить клиента":
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Да", "Нет")
        user_states[message.chat.id] = "confirm_delete"
        bot.send_message(message.chat.id, "Удалить клиента? Подтвердите.", reply_markup=markup)
    elif choice == "📎 Резервные коды":
        user_states[message.chat.id] = "edit_attachment"
        bot.send_message(message.chat.id, "Пришлите новый скрин/файл с кодами для замены.")
    else:
        bot.send_message(message.chat.id, "Эта функция редактирования ещё не реализована.")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "confirm_delete")
def delete_from_edit(message):
    if message.text.lower() == "да":
        delete_client(client_data[message.chat.id])
        bot.send_message(message.chat.id, "✅ Клиент удалён.")
    else:
        bot.send_message(message.chat.id, "Удаление отменено.")
    reset_user_state(message.chat.id)
    show_menu(message)

@bot.message_handler(content_types=["photo", "document"])
def replace_attachment(message):
    cid = message.chat.id
    if user_states.get(cid) == "edit_attachment":
        phone = client_data[cid]
        folder = f"attachments/{phone}"
        os.makedirs(folder, exist_ok=True)
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))
        file = message.photo[-1] if message.photo else message.document
        file_info = bot.get_file(file.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        filename = file_info.file_path.split("/")[-1]
        with open(os.path.join(folder, filename), "wb") as f:
            f.write(downloaded_file)
        bot.send_message(cid, "✅ Вложения обновлены.")
        reset_user_state(cid)
        show_menu(message)

# 🔍 Найти клиента
@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "🔍 Найти клиента")
def start_search(message):
    bot.send_message(message.chat.id, "Введите номер телефона или ник клиента:")
    user_states[message.chat.id] = "search_request"

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "search_request")
def handle_search(message):
    phone = message.text.strip()
    data = get_client_block(phone)
    if not data:
        bot.send_message(message.chat.id, "Клиент не найден.")
        reset_user_state(message.chat.id)
        return show_menu(message)
    user_states[message.chat.id] = "edit_menu"
    client_data[message.chat.id] = phone
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("📱 Телефон", "📅 Дата рождения")
    markup.add("🔐 Аккаунт", "🕹 Подписка")
    markup.add("🎮 Игры", "📎 Резервные коды")
    markup.add("🗑 Удалить клиента", "❌ Отмена")
    bot.send_message(message.chat.id, f"Данные клиента:\n{data}", reply_markup=markup)

# 📋 Список клиентов
@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "📋 Список клиентов")
def handle_list_clients(message):
    clients = get_all_clients_text()
    if not clients:
        return bot.send_message(message.chat.id, "Клиентов пока нет.")
    for entry in clients:
        bot.send_message(message.chat.id, entry)

# 🧨 Очистка базы
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

# ⏰ Уведомления
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
                    msg = f"Напоминание:\\nУ клиента {phone} заканчивается подписка {typ} ({months}м) завтра ({end})"
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("Открыть данные клиента", callback_data=f"open_client_{phone}"))
                    bot.send_message(ALLOWED_USER_ID, msg, reply_markup=markup)
                if bday:
                    bot.send_message(ALLOWED_USER_ID, f"🎉 У клиента сегодня день рождения:\\n{phone}")
                    data = get_client_block(phone)
                    if data:
                        bot.send_message(ALLOWED_USER_ID, data)
        time.sleep(3600)

# 🔧 Запуск
init_db()
threading.Thread(target=notify_loop, daemon=True).start()
bot.infinity_polling()
