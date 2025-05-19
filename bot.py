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
        def send_client_data_with_attachment(chat_id, phone):
    data = get_client_block(phone)
    bot.send_message(chat_id, data)
    attach_path = f"attachments/{phone}"
    if os.path.isdir(attach_path):
        files = os.listdir(attach_path)
        for f in files:
            full_path = os.path.join(attach_path, f)
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                with open(full_path, "rb") as img:
                    bot.send_photo(chat_id, img, caption="Резервные коды")
            else:
                with open(full_path, "rb") as doc:
                    bot.send_document(chat_id, doc, caption="Резервные коды")

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "✏️ Редактировать")
def edit_client_start(message):
    user_states[message.chat.id] = "edit_request"
    bot.send_message(message.chat.id, "Введите номер телефона или ник клиента для редактирования:")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id) == "edit_request")
def handle_edit_request(message):
    query = message.text.strip()
    if not get_client_block(query):
        bot.send_message(message.chat.id, "Клиент не найден.")
        reset_user_state(message.chat.id)
        return
    user_states[message.chat.id] = f"edit_menu_{query}"
    send_client_data_with_attachment(message.chat.id, query)
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📱 Телефон", "📅 Дата рождения", "🔐 Аккаунт")
    markup.add("🕹 Подписку", "🎮 Игры", "🗂 Вложения")
    markup.add("🗑 Удалить клиента", "❌ Отмена")
    bot.send_message(message.chat.id, "Что хотите изменить?", reply_markup=markup)

@bot.message_handler(func=lambda m: is_authorized(m) and m.text == "🗂 Вложения")
def handle_attachment_edit(message):
    phone = user_states.get(message.chat.id, "").replace("edit_menu_", "")
    if not phone:
        return bot.send_message(message.chat.id, "Сначала выберите клиента.")
    folder = f"attachments/{phone}"
    if os.path.isdir(folder) and os.listdir(folder):
        bot.send_message(message.chat.id, "Файл найден. Что сделать?")
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Удалить вложение", "Заменить вложение")
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)
        user_states[message.chat.id] = f"edit_attach_{phone}"
    else:
        bot.send_message(message.chat.id, "Вложение отсутствует.")

@bot.message_handler(func=lambda m: is_authorized(m) and user_states.get(m.chat.id, "").startswith("edit_attach_"))
def handle_attachment_choice(message):
    cid = message.chat.id
    phone = user_states[cid].replace("edit_attach_", "")
    folder = f"attachments/{phone}"
    if message.text.lower().startswith("удалить"):
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))
        bot.send_message(cid, "Вложение удалено.")
    elif message.text.lower().startswith("заменить"):
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))
        user_states[cid] = "awaiting_attachment"
        client_data[cid] = [phone]
        bot.send_message(cid, "Пришли новый файл для вложения:")
    else:
        bot.send_message(cid, "Выберите 'Удалить вложение' или 'Заменить вложение'.")