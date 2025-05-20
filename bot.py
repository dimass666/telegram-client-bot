import telebot
from telebot import types
from database import init_db, add_client
from datetime import datetime, timedelta

bot = telebot.TeleBot("7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8")
admin_id = 350902460

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
def step1_choose_input_method(message):
    if message.from_user.id != admin_id:
        return
    client_data.clear()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Номер телефона", "Telegram")
    bot.send_message(message.chat.id, "Шаг 1: Выберите способ идентификации клиента", reply_markup=markup)
    bot.register_next_step_handler(message, step2_get_identifier)

def step2_get_identifier(message):
    client_data["input_method"] = message.text
    bot.send_message(message.chat.id, f"Введите {message.text.lower()}:")
    bot.register_next_step_handler(message, step3_birth_prompt)

def step3_birth_prompt(message):
    client_data["username"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Есть", "Нету")
    bot.send_message(message.chat.id, "Шаг 2: Есть ли дата рождения?", reply_markup=markup)
    bot.register_next_step_handler(message, step4_birth_check)

def step4_birth_check(message):
    if message.text == "Есть":
        bot.send_message(message.chat.id, "Введите дату рождения (дд.мм.гггг):")
        bot.register_next_step_handler(message, step5_birth_date)
    else:
        client_data["birth_date"] = "отсутствует"
        step6_account_prompt(message)

def step5_birth_date(message):
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        client_data["birth_date"] = message.text
    except:
        client_data["birth_date"] = "отсутствует"
    step6_account_prompt(message)

def step6_account_prompt(message):
    bot.send_message(message.chat.id, "Шаг 3: Введите данные аккаунта.\n\nФормат:\nemail\nпароль\nпароль от почты (может быть пустым)")
    bot.register_next_step_handler(message, step7_account_data)

def step7_account_data(message):
    lines = message.text.split('\n')
    email = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    mail_pass = lines[2] if len(lines) > 2 else ""
    client_data["email"] = email
    client_data["account_password"] = f"{email};{password}"
    client_data["mail_password"] = mail_pass
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play")
    bot.send_message(message.chat.id, "Шаг 4: Какая подписка оформлена?", reply_markup=markup)
    bot.register_next_step_handler(message, step8_subscription_type)

def step8_subscription_type(message):
    client_data["sub_type"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("12м", "3м", "1м")
    bot.send_message(message.chat.id, "Шаг 5: На какой срок подписка?", reply_markup=markup)
    bot.register_next_step_handler(message, step9_subscription_duration)

def step9_subscription_duration(message):
    client_data["sub_duration"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("(укр)", "(тур)", "(другой)")
    bot.send_message(message.chat.id, "Шаг 6: Выберите регион подписки", reply_markup=markup)
    bot.register_next_step_handler(message, step10_subscription_region)

def step10_subscription_region(message):
    client_data["region"] = message.text
    bot.send_message(message.chat.id, "Шаг 7: Когда оформлена подписка? (дд.мм.гггг)")
    bot.register_next_step_handler(message, step11_subscription_start)

def step11_subscription_start(message):
    try:
        start_date = datetime.strptime(message.text, "%d.%m.%Y")
        duration = client_data["sub_duration"]
        if duration == "1м":
            end_date = start_date + timedelta(days=30)
        elif duration == "3м":
            end_date = start_date + timedelta(days=90)
        elif duration == "12м":
            end_date = start_date + timedelta(days=365)
        else:
            end_date = start_date
        client_data["subscription_name"] = f"{client_data['sub_type']} {client_data['sub_duration']} {client_data['region']}"
        client_data["subscription_start"] = message.text
        client_data["subscription_end"] = end_date.strftime("%d.%m.%Y")
    except:
        client_data["subscription_name"] = "Нету"
        client_data["subscription_start"] = ""
        client_data["subscription_end"] = ""
    bot.send_message(message.chat.id, "Шаг 8: Оформлены ли игры?", reply_markup=create_yes_no())
    bot.register_next_step_handler(message, step12_games_prompt)

def create_yes_no():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет")
    return markup

def step12_games_prompt(message):
    if message.text == "Да":
        bot.send_message(message.chat.id, "Введите список игр (по строкам):")
        bot.register_next_step_handler(message, step13_save_client)
    else:
        client_data["games"] = ""
        step13_save_client(message)

def step13_save_client(message):
    if not client_data.get("games"):
        games = message.text.split('\n')
        client_data["games"] = " —— ".join(games)
    data = (
        client_data.get("username", ""),
        client_data.get("birth_date", ""),
        client_data.get("email", ""),
        client_data.get("account_password", ""),
        client_data.get("mail_password", ""),
        client_data.get("subscription_name", "Нету"),
        client_data.get("subscription_start", ""),
        client_data.get("subscription_end", ""),
        client_data.get("region", ""),
        client_data.get("games", "")
    )
    add_client(data)
    bot.send_message(message.chat.id, f"✅ {client_data['username']} успешно добавлен!", reply_markup=main_menu)

if __name__ == "__main__":
    init_db()
    bot.polling(none_stop=True)