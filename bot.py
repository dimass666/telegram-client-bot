import telebot
import os
from database import init_db
from scheduler import start_scheduler

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

AUTHORIZED_USERS = []  # Добавь сюда свой Telegram ID

@bot.message_handler(commands=["start"])
def start(message):
    if message.from_user.id not in AUTHORIZED_USERS:
        return
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["➕ Добавить", "✏️ Редактировать", "🔍 Найти клиента", "🗑 Удалить",
               "📋 Список клиентов", "📊 Кол-во по регионам", "⬇️ Выгрузить базу", "🧨 Очистить всю базу"]
    markup.add(*buttons)
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=markup)

if __name__ == "__main__":
    init_db()
    start_scheduler(bot)
    bot.polling(none_stop=True)