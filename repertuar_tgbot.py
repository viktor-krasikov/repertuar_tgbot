import logging
import os
import re
from logging.handlers import RotatingFileHandler

import mysql.connector
import telebot
from telebot import types

import repertuar_env as env
from storage_manager.mysql_storage_manager import MysqlStorageManager
from storage_manager.postgresql_storage_manager import PostgresqlStorageManager

# Создание директории для логов, если она еще не создана
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Имя файла и путь к логам
log_file = os.path.join(log_dir, 'repertuar_bot.log')

# Создаем logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Создаем обработчик для ротации логов
handler = RotatingFileHandler(log_file, maxBytes=100000, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Добавляем обработчик к logger
logger.addHandler(handler)

# Пример логирования
logger.info('Repertuar bot started')

# Оставьте нужный тип сервера, ненужный - закомментируйте
# storage = MysqlStorageManager(logger, env.MYSQL_CONNECTOR_PARAMS)
storage = PostgresqlStorageManager(logger, env.POSTGRESQL_CONNECTOR_PARAMS)

# Инициализация бота
bot = telebot.TeleBot(env.TELEGRAM_BOT_TOKEN)
telegram_admin_chat_id = None


def send_admin_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('/random')
    btn2 = types.KeyboardButton('/random20')
    btn3 = types.KeyboardButton('/stats')
    btn4 = types.KeyboardButton('/add')
    btn5 = types.KeyboardButton('/addcsv')
    btn6 = types.KeyboardButton('/backup')
    btn7 = types.KeyboardButton('/tags')
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    bot.send_message(chat_id, "Выберите пункт меню", reply_markup=markup)


def send_client_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Случайная композиция')
    btn2 = types.KeyboardButton('Заказать композицию')
    btn3 = types.KeyboardButton('Написать отзыв')
    btn4 = types.KeyboardButton('Поддержать музыканта')
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(chat_id, "Выберите пункт меню", reply_markup=markup)


@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.username == env.TELEGRAM_ADMIN_USERNAME:
        global telegram_admin_chat_id
        if telegram_admin_chat_id is None:
            telegram_admin_chat_id = message.chat.id
        send_admin_menu(message.chat.id)
    else:
        bot.send_message(message.chat.id, "Добро пожаловать!")
        send_client_menu(message.chat.id)


@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.username == env.TELEGRAM_ADMIN_USERNAME:
        count = storage.get_songs_count()
        bot.send_message(message.chat.id, f"У вас {count} музыкальных композиций в репертуаре")
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде")


@bot.message_handler(commands=['tags'])
def tags(message):
    tag_list = storage.get_tags()
    bot.send_message(message.chat.id, f"Список всех тегов: {tag_list}")


# Команда /add для добавления музыкального произведения
@bot.message_handler(commands=['add'])
def add_music(message):
    if message.from_user.username == env.TELEGRAM_ADMIN_USERNAME:
        bot.send_message(message.chat.id, "Введите название музыкального произведения:")
        bot.register_next_step_handler(message, add_artist)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")


def add_artist(message):
    title = message.text
    bot.send_message(message.chat.id, "Введите исполнителя:")
    bot.register_next_step_handler(message, add_tags, title)


def add_tags(message, title):
    artist = message.text
    bot.send_message(message.chat.id, "Введите теги через запятую:")
    bot.register_next_step_handler(message, add_mark, title, artist)


def add_mark(message, title, artist):
    tags = message.text
    bot.send_message(message.chat.id, "Введите оценку от 0 до 5:")
    bot.register_next_step_handler(message, add_to_database, title, artist, tags)


def add_to_database(message, title, artist, tags):
    try:
        mark = int(message.text)
        storage.add_song(title, artist, tags, mark)
        bot.send_message(message.chat.id, f"Музыкальное произведение '{title}' успешно добавлено!")
    except mysql.connector.errors.IntegrityError as e:
        bot.send_message(message.chat.id, f"Музыкальное произведение '{title}' уже есть в БД")
    except Exception as e:
        logger.error(e)
        bot.send_message(message.chat.id, f"Ошибка при добавлении '{e}'")


# Команда /addcsv для добавления нескольких музыкальных произведений из CSV
@bot.message_handler(commands=['addcsv'])
def add_csv(message):
    if message.from_user.username == env.TELEGRAM_ADMIN_USERNAME:
        bot.send_message(message.chat.id, "Вставьте список мулькальных композиций в формате CSV:\n"
                                          "Название;Исполнитель;Тэги через запятую (не обязательно);"
                                          "Оценка от 0 до 5 (не обязательно)\n\n"
                                          "Или отправьте CSV-файл с вышеописанным содержимым.")
        bot.register_next_step_handler(message, process_csv_input)  # Регистрируем следующий шаг обработки
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")


def process_csv_input(message):
    """Процесс обработки входного текста или файла"""
    if message.from_user.username == env.TELEGRAM_ADMIN_USERNAME:
        if message.content_type in ['text', 'document']:
            if message.content_type == 'text':
                music_data = message.text.split("\n")
            elif message.content_type == 'document':
                # Получаем файл
                file_info = bot.get_file(message.document.file_id)
                music_data = bot.download_file(file_info.file_path).decode('utf-8').split("\n")
            result_as_text = insert_csv_data(music_data)
            bot.send_message(message.chat.id, result_as_text)
        else:
            bot.send_message(chat_id=message.chat.id,
                             text="Неподдерживаемый тип сообщения. Пожалуйста, отправьте текст или CSV-файл.")
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")


def insert_csv_data(music_data):
    logger.info("Получено CSV-сообщение с " + str(len(music_data)) + " композиций")
    count_success, count_duplicates, count_dberror, count_error, count_skipped = 0, 0, 0, 0, 0
    for data in music_data:
        row = re.split(";", data)
        if 2 <= len(row) <= 4:
            title, artist = row[0], row[1]
            tags = row[2] if len(row) > 2 else ""
            mark = row[3] if len(row) > 3 else 0
            logger.info(f"Добавляется: {artist}, {title}, {tags}, {mark}")
            result = storage.add_song(title, artist, tags, mark)
            if result == 0:
                count_success += 1
            elif result == 1:
                count_duplicates += 1
            elif result == 2:
                count_dberror += 1
            else:
                count_error += 1
        else:
            count_skipped += 1

    if count_duplicates == 0 and count_dberror == 0 and count_error == 0 and count_skipped == 0:
        result_text = f"Музыкальные композиции успешно добавлены ({count_success} шт)"
    elif count_success > 0:
        result_text = f"Музыкальные композиции успешно добавлены ({count_success} шт)\n" \
                      f"Дубликатов - {count_duplicates} шт\n" \
                      f"Ошибок с БД - {count_dberror} шт\n" \
                      f"Прочих ошибок - {count_error} шт\n" \
                      f"Пропущено - {count_skipped} шт"
    else:
        result_text = f"Музыкальные композиции не были добавлены:\n" \
                      f"Дубликатов - {count_duplicates} шт\n" \
                      f"Ошибок с БД - {count_dberror} шт\n" \
                      f"Прочих ошибок - {count_error} шт\n" \
                      f"Пропущено - {count_skipped} шт"
    return result_text


# Команда /random для получения случайного музыкального произведения
@bot.message_handler(commands=['random'])
def random_music(message):
    song = storage.get_random_song()
    if song is None:
        bot.send_message(message.chat.id, "Нет композиций в базе данных")
        return

    # "80е,советские,ретро" => "#80е #советские #ретро"
    tags_list = " ".join(["#" + tag.strip().replace(" ", "_") for tag in song.tags.split(',') if tag])

    if message.from_user.username == env.TELEGRAM_ADMIN_USERNAME:
        markup = types.InlineKeyboardMarkup(row_width=7)
        buttons = [types.InlineKeyboardButton(i_mark + ("✔️" if i_mark == str(song.mark) else ""),
                                              callback_data=f"update_rating_{song.id}_{i_mark}")
                   for i_mark in "012345"]
        buttons.append(types.InlineKeyboardButton("✍️", callback_data=f"edit_{song.id}"))
        markup.add(*buttons)

        bot.send_message(message.chat.id, f"{song.artist} - {song.title}\n{tags_list}",
                         reply_markup=markup)
    #        bot.register_next_step_handler(message, update_rating, result[0])
    else:
        bot.send_message(message.chat.id, f"{song.artist} - {song.title}\n{tags_list}")


def update_rating(message, repertuar_id, mark):
    try:
        rows_updated = storage.update_rating(repertuar_id, mark)

        if rows_updated == 1:
            markup = types.InlineKeyboardMarkup(row_width=7)
            buttons = [types.InlineKeyboardButton(i_mark + ("✔️" if i_mark == str(mark) else ""),
                                                  callback_data=f"update_rating_{repertuar_id}_{i_mark}")
                       for i_mark in "012345"]
            markup.add(*buttons)
            bot.edit_message_reply_markup(message.chat.id, message.id, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Композиция не найдена в базе данных")
    except Exception as e:
        logger.error(e)
        bot.send_message(message.chat.id, "Не удалось сохранить оценку, смотрите логи")


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("update_rating_"):
        repertuar_id, mark = re.findall(r"\d+", call.data)
        update_rating(call.message, int(repertuar_id), int(mark))


@bot.message_handler(func=lambda message: message.text == 'Заказать композицию')
def zakaz_song(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    itembtn = types.KeyboardButton('Назад')
    markup.add(itembtn)
    msg = bot.send_message(message.chat.id,
                           "Введите название песни, которую вы хотели бы заказать или нажмите 'Назад' для возврата.",
                           reply_markup=markup)
    bot.register_next_step_handler(msg, send_composition_to_admin)


def send_composition_to_admin(message):
    if message.text.lower() != 'назад':
        # TODO в таблицу какую-нибудь сохранять
        composition = message.text
        global telegram_admin_chat_id
        if telegram_admin_chat_id is not None:
            bot.send_message(telegram_admin_chat_id,
                             f"Пользователь {message.from_user.username} заказал композицию: {composition}")
            bot.send_message(message.chat.id, "Заявка отправлена")
        else:
            bot.send_message(message.chat.id, "Не удалось отправить заявку музыканту")
    send_client_menu(message.chat.id)


@bot.message_handler(commands=['backup'])
def backup_command(message):
    """Обработчик команды /backup"""
    try:
        file_path = 'backup_repertuar.csv'  # Путь к файлу
        backup_file = storage.backup(file_path)
        with open(backup_file, 'rb') as file:
            bot.send_document(chat_id=message.chat.id, document=file)
        os.remove(backup_file)  # Удаляем файл после отправки
    except Exception as e:
        bot.send_message(chat_id=message.chat.id, text=f"Произошла ошибка: {str(e)}")


# Запуск бота
bot.polling()
