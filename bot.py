import telebot
import os
from dotenv import load_dotenv
from database import init_db, add_client, get_all_clients
from telebot import types

load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))
admin_id = int(os.getenv("ADMIN_ID"))

main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.row("➕ Добавить", "✏️ Редактировать")
main_menu.row("🔍 Найти клиента", "🗑 Удалить")
main_menu.row("📋 Список клиентов", "📊 Кол-во по регионам")
main_menu.row("⬇️ Выгрузить базу", "🧨 Очистить всю базу")

client_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id != admin_id:
        return bot.send_message(message.chat.id, "Доступ запрещён.")
    bot.send_message(message.chat.id, "Добро пожаловать в CRM для PS клиентов!", reply_markup=main_menu)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def handle_add(message):
    if message.from_user.id != admin_id:
        return
    bot.send_message(message.chat.id, "Введите Телефон или ник:")
    bot.register_next_step_handler(message, ask_birth_date)

def ask_birth_date(message):
    client_data["username"] = message.text
    bot.send_message(message.chat.id, "Введите дату рождения (дд.мм.гггг):")
    bot.register_next_step_handler(message, ask_email)

def ask_email(message):
    client_data["birth_date"] = message.text
    bot.send_message(message.chat.id, "Введите email:")
    bot.register_next_step_handler(message, ask_account_password)

def ask_account_password(message):
    client_data["email"] = message.text
    bot.send_message(message.chat.id, "Введите пароль от аккаунта:")
    bot.register_next_step_handler(message, ask_mail_password)

def ask_mail_password(message):
    client_data["account_password"] = message.text
    bot.send_message(message.chat.id, "Введите пароль от почты (может быть пустым):")
    bot.register_next_step_handler(message, ask_subscription)

def ask_subscription(message):
    client_data["mail_password"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет")
    bot.send_message(message.chat.id, "Есть ли подписка?", reply_markup=markup)
    bot.register_next_step_handler(message, handle_subscription_choice)

def handle_subscription_choice(message):
    if message.text == "Да":
        bot.send_message(message.chat.id, "Введите название подписки:")
        bot.register_next_step_handler(message, ask_subscription_start)
    else:
        client_data["subscription_name"] = "Нету"
        client_data["subscription_start"] = ""
        client_data["subscription_end"] = ""
        client_data["region"] = ""
        ask_games(message)

def ask_subscription_start(message):
    client_data["subscription_name"] = message.text
    bot.send_message(message.chat.id, "Введите дату начала подписки (дд.мм.гггг):")
    bot.register_next_step_handler(message, handle_subscription_start)

def handle_subscription_start(message):
    from datetime import datetime, timedelta
    try:
        start = datetime.strptime(message.text, "%d.%m.%Y")
        client_data["subscription_start"] = message.text
        if "1м" in client_data["subscription_name"]:
            end = start + timedelta(days=30)
        elif "3м" in client_data["subscription_name"]:
            end = start + timedelta(days=90)
        elif "12м" in client_data["subscription_name"]:
            end = start + timedelta(days=365)
        else:
            end = start
        client_data["subscription_end"] = end.strftime("%d.%m.%Y")
        client_data["region"] = "(тур)" if "тур" in client_data["subscription_name"].lower() else "(укр)" if "укр" in client_data["subscription_name"].lower() else "(другое)"
        ask_games(message)
    except:
        bot.send_message(message.chat.id, "Неверный формат даты. Повторите:")
        bot.register_next_step_handler(message, handle_subscription_start)

def ask_games(message):
    bot.send_message(message.chat.id, "Введите список игр (по строкам):")
    bot.register_next_step_handler(message, save_client)

def save_client(message):
    client_data["games"] = message.text
    data = (
        client_data["username"],
        client_data["birth_date"],
        client_data["email"],
        client_data["account_password"],
        client_data["mail_password"],
        client_data.get("subscription_name", "Нету"),
        client_data.get("subscription_start", ""),
        client_data.get("subscription_end", ""),
        client_data.get("region", ""),
        client_data["games"]
    )
    add_client(data)
    bot.send_message(message.chat.id, "Клиент добавлен!", reply_markup=main_menu)

@bot.message_handler(func=lambda m: m.text == "📋 Список клиентов")
def list_clients(message):
    clients = get_all_clients()
    for client in clients:
        text = (
            f"Имя: {client[1]}
"
            f"Дата рождения: {client[2]}
"
            f"Email: {client[3]}
"
            f"Пароль: {client[4]}
"
            f"Почта: {client[5]}
"
            f"Подписка: {client[6]} ({client[7]} - {client[8]})
"
            f"Регион: {client[9]}
"
            f"Игры:
{client[10]}"
        )
        bot.send_message(message.chat.id, text)

if __name__ == "__main__":
    init_db()
    bot.polling(none_stop=True)
