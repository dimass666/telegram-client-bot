import telebot
from telebot import types
from database import init_db, add_client, get_client_by_identifier, update_client_field
from datetime import datetime, timedelta

bot = telebot.TeleBot("7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8")
admin_id = 350902460
client_data = {}

main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.row("➕ Добавить", "🔍 Найти клиента")

def clear_chat(chat_id):
    try:
        msgs = bot.get_chat_history(chat_id, limit=20)
        for msg in msgs:
            try:
                bot.delete_message(chat_id, msg.message_id)
            except:
                continue
    except:
        pass

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id != admin_id:
        return bot.send_message(message.chat.id, "Доступ запрещён.")
    bot.send_message(message.chat.id, "CRM для PS клиентов", reply_markup=main_menu)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def start_add(message):
    if message.from_user.id != admin_id:
        return
    client_data.clear()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Номер телефона", "Telegram", "Отмена")
    bot.send_message(message.chat.id, "Шаг 1: Введите способ идентификации клиента", reply_markup=markup)
    bot.register_next_step_handler(message, get_identifier)

def get_identifier(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return
    client_data["method"] = message.text
    bot.send_message(message.chat.id, f"Введите {message.text.lower()}:")
    bot.register_next_step_handler(message, ask_birth_option)

def ask_birth_option(message):
    client_data["username"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Есть", "Нету", "Отмена")
    bot.send_message(message.chat.id, "Шаг 2: Есть ли дата рождения?", reply_markup=markup)
    bot.register_next_step_handler(message, ask_birth_date)

def ask_birth_date(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return
    if message.text == "Есть":
        bot.send_message(message.chat.id, "Введите дату рождения (дд.мм.гггг):")
        bot.register_next_step_handler(message, collect_birth_date)
    else:
        client_data["birth_date"] = "отсутствует"
        ask_account_info(message)

def collect_birth_date(message):
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        client_data["birth_date"] = message.text
    except:
        client_data["birth_date"] = "отсутствует"
    ask_account_info(message)

def ask_account_info(message):
    bot.send_message(message.chat.id, "Шаг 3: Введите:
email
пароль
пароль от почты (можно пусто)")
    bot.register_next_step_handler(message, process_account_info)

def process_account_info(message):
    lines = message.text.split("\n")
    email = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    mail_pass = lines[2] if len(lines) > 2 else ""
    client_data["email"] = email
    client_data["account_password"] = f"{email};{password}"
    client_data["mail_password"] = mail_pass
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет", "Отмена")
    bot.send_message(message.chat.id, "Шаг 4: Оформлена ли подписка?", reply_markup=markup)
    bot.register_next_step_handler(message, ask_subscriptions_count)

def ask_subscriptions_count(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return
    if message.text == "Нет":
        client_data["subscription_name"] = "Нету"
        client_data["subscription_start"] = ""
        client_data["subscription_end"] = ""
        client_data["region"] = ""
        ask_games_option(message)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Одна", "Две", "Отмена")
        bot.send_message(message.chat.id, "Сколько подписок оформлено?", reply_markup=markup)
        bot.register_next_step_handler(message, choose_first_subscription)

def choose_first_subscription(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return
    client_data["subs_total"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play")
    bot.send_message(message.chat.id, "Выберите первую подписку:", reply_markup=markup)
    bot.register_next_step_handler(message, collect_first_subscription)

def collect_first_subscription(message):
    client_data["sub1_type"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("12м", "3м", "1м", "Отмена")
    bot.send_message(message.chat.id, "Срок первой подписки:", reply_markup=markup)
    bot.register_next_step_handler(message, collect_first_duration)

def collect_first_duration(message):
    client_data["sub1_duration"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("(укр)", "(тур)", "(другой)")
    bot.send_message(message.chat.id, "Регион первой подписки:", reply_markup=markup)
    bot.register_next_step_handler(message, collect_first_region)

def collect_first_region(message):
    client_data["sub1_region"] = message.text
    bot.send_message(message.chat.id, "Дата оформления первой подписки (дд.мм.гггг):")
    bot.register_next_step_handler(message, calculate_subscriptions)

def calculate_subscriptions(message):
    try:
        start = datetime.strptime(message.text, "%d.%m.%Y")
    except:
        start = datetime.now()
    client_data["subscription_start"] = start.strftime("%d.%m.%Y")
    duration = client_data["sub1_duration"]
    end = start + (timedelta(days=365) if duration == "12м" else timedelta(days=90) if duration == "3м" else timedelta(days=30))
    client_data["subscription_end"] = end.strftime("%d.%m.%Y")
    client_data["region"] = client_data["sub1_region"]
    client_data["subscription_name"] = f"{client_data['sub1_type']} {client_data['sub1_duration']} {client_data['sub1_region']}"

    if client_data.get("subs_total") == "Две":
        # предлагать вторую только из другой категории
        if "EA Play" in client_data["sub1_type"]:
            second = ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]
        else:
            second = ["EA Play"]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for s in second:
            markup.add(s)
        bot.send_message(message.chat.id, "Выберите вторую подписку:", reply_markup=markup)
        bot.register_next_step_handler(message, add_second_subscription)
    else:
        ask_games_option(message)

def add_second_subscription(message):
    client_data["sub2_type"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("12м", "3м", "1м", "Отмена")
    bot.send_message(message.chat.id, "Срок второй подписки:", reply_markup=markup)
    bot.register_next_step_handler(message, second_sub_duration)

def second_sub_duration(message):
    client_data["sub2_duration"] = message.text
    bot.send_message(message.chat.id, "Регион второй подписки:")
    bot.register_next_step_handler(message, second_sub_region)

def second_sub_region(message):
    client_data["sub2_region"] = message.text
    bot.send_message(message.chat.id, "Дата оформления второй подписки (дд.мм.гггг):")
    bot.register_next_step_handler(message, complete_subscription_info)

def complete_subscription_info(message):
    try:
        start = datetime.strptime(message.text, "%d.%m.%Y")
    except:
        start = datetime.now()
    duration = client_data["sub2_duration"]
    end = start + (timedelta(days=365) if duration == "12м" else timedelta(days=90) if duration == "3м" else timedelta(days=30))
    sub1 = f"{client_data['sub1_type']} {client_data['sub1_duration']} {client_data['sub1_region']}"
    sub2 = f"{client_data['sub2_type']} {client_data['sub2_duration']} {client_data['sub2_region']}"
    client_data["subscription_name"] = f"{sub1} + {sub2}"
    client_data["region"] = f"{client_data['sub1_region']}, {client_data['sub2_region']}"
    client_data["subscription_end"] = end.strftime("%d.%m.%Y")
    ask_games_option(message)

def ask_games_option(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет", "Отмена")
    bot.send_message(message.chat.id, "Есть ли игры у клиента?", reply_markup=markup)
    bot.register_next_step_handler(message, collect_games)

def collect_games(message):
    if message.text == "Нет":
        client_data["games"] = ""
        finish_add(message)
    elif message.text == "Да":
        bot.send_message(message.chat.id, "Введите список игр (по строкам):")
        bot.register_next_step_handler(message, save_games)
    else:
        clear_chat(message.chat.id)

def save_games(message):
    games = message.text.split("\n")
    client_data["games"] = " —— ".join(games)
    finish_add(message)

def finish_add(message):
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
    clear_chat(message.chat.id)
    bot.send_message(message.chat.id, f"✅ {client_data['username']} успешно добавлен!", reply_markup=main_menu)

if __name__ == "__main__":
    init_db()
    bot.polling(none_stop=True)

@bot.message_handler(func=lambda m: m.text == "🔍 Найти клиента")
def search_client(message):
    if message.from_user.id != admin_id:
        return
    msg = bot.send_message(message.chat.id, "Введите номер телефона или Telegram:")
    bot.register_next_step_handler(msg, show_client_data)

def show_client_data(message):
    identifier = message.text.strip()
    client = get_client_by_identifier(identifier)
    if not client:
        return bot.send_message(message.chat.id, "Клиент не найден.")

    id_, username, birth, email, acc_pass, mail_pass, sub_name, sub_start, sub_end, region, games = client

    text = f"""Найден клиент:
Ник / Телефон: {username}
Дата рождения: {birth}
Аккаунт: {acc_pass}
Пароль от почты: {mail_pass}
Подписка: {sub_name}
Срок: {sub_start} - {sub_end}
Регион: {region}
Игры:
{games if games else 'Нет'}

Что хотите изменить?"""

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Изменить номер", "Изменить дату рождения")
    markup.add("Изменить аккаунт", "Изменить подписку")
    markup.add("Изменить игры", "Отмена")
    bot.send_message(message.chat.id, text, reply_markup=markup)
    client_data["id"] = id_
    bot.register_next_step_handler(message, handle_edit_choice)

def handle_edit_choice(message):
    if message.text == "Изменить номер":
        msg = bot.send_message(message.chat.id, "Введите новый номер или Telegram:")
        bot.register_next_step_handler(msg, lambda m: update_field(m, "username"))
    elif message.text == "Изменить дату рождения":
        msg = bot.send_message(message.chat.id, "Введите новую дату рождения (дд.мм.гггг):")
        bot.register_next_step_handler(msg, lambda m: update_field(m, "birth_date"))
    elif message.text == "Изменить аккаунт":
        msg = bot.send_message(message.chat.id, "Введите:
email
пароль
пароль от почты")
        bot.register_next_step_handler(msg, update_account_info)
    elif message.text == "Изменить подписку":
        update_subscription_flow(message)
    elif message.text == "Изменить игры":
        msg = bot.send_message(message.chat.id, "Введите список игр (по строкам):")
        bot.register_next_step_handler(msg, update_games)
    else:
        bot.send_message(message.chat.id, "Отмена", reply_markup=main_menu)

def update_field(message, field):
    update_client_field(client_data["id"], field, message.text.strip())
    bot.send_message(message.chat.id, "Изменено!", reply_markup=main_menu)

def update_account_info(message):
    lines = message.text.split("\n")
    email = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    mail_pass = lines[2] if len(lines) > 2 else ""
    update_client_field(client_data["id"], "email", email)
    update_client_field(client_data["id"], "account_password", f"{email};{password}")
    update_client_field(client_data["id"], "mail_password", mail_pass)
    bot.send_message(message.chat.id, "Аккаунт обновлён!", reply_markup=main_menu)

def update_games(message):
    games = message.text.split("\n")
    games_joined = " —— ".join(games)
    update_client_field(client_data["id"], "games", games_joined)
    bot.send_message(message.chat.id, "Игры обновлены!", reply_markup=main_menu)

def update_subscription_flow(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Заменить текущую", "Добавить вторую", "Отмена")
    bot.send_message(message.chat.id, "Что хотите сделать с подпиской?", reply_markup=markup)
    bot.register_next_step_handler(message, subscription_update_step)

def subscription_update_step(message):
    current = get_client_by_identifier(client_data["id"])
    current_sub = current[6] if current else ""
    if message.text == "Заменить текущую":
        bot.send_message(message.chat.id, "Введите новую подписку (название, срок, регион):")
        bot.register_next_step_handler(message, lambda m: update_field(m, "subscription_name"))
    elif message.text == "Добавить вторую":
        if "EA Play" in current_sub:
            choices = ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]
        else:
            choices = ["EA Play"]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for item in choices:
            markup.add(item)
        bot.send_message(message.chat.id, "Выберите вторую подписку:", reply_markup=markup)
        bot.register_next_step_handler(message, lambda m: handle_second_sub(m, current_sub))
    else:
        bot.send_message(message.chat.id, "Отмена", reply_markup=main_menu)

def handle_second_sub(message, current_sub):
    new = message.text.strip()
    combined = f"{current_sub} + {new}"
    update_client_field(client_data["id"], "subscription_name", combined)
    bot.send_message(message.chat.id, "Подписка обновлена!", reply_markup=main_menu)