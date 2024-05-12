import logging
import os
import re
from logging.handlers import RotatingFileHandler

import mysql.connector
import telebot
from telebot import types

import repertuar_env as env

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

db, cursor = None, None


# Функция для проверки  соединения
def is_connected():
    if db is not None and cursor is not None:
        try:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result is not None:
                return True
        except mysql.connector.Error as e:
            logger.error(f"Error checking connection: {e}")
        except Exception as e:
            logger.error(f"Unknown error in is_connected: {e}")
    return False


# Подключение к базе данных MySQL
def connect_if_need():
    if not is_connected():
        logger.info("Попытка соединения с БД")
        global db, cursor
        db = mysql.connector.connect(**env.MYSQL_CONNECTOR_PARAMS)
        cursor = db.cursor()
        logger.info("Соединение с БД установлено")


# Создание таблицы 'repertuar', если её нет
connect_if_need()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS repertuar (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) DEFAULT '',
        artist VARCHAR(255) DEFAULT '',
        tags VARCHAR(255) DEFAULT '',
        open_time TIMESTAMP DEFAULT NOW(),
        content TEXT,
        mark INT DEFAULT 0,
        UNIQUE(title, artist)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""");

# Инициализация бота
bot = telebot.TeleBot(env.TELEGRAM_BOT_TOKEN)


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
        connect_if_need()
        cursor.execute(
            "INSERT INTO repertuar (title, artist, tags, open_time, content, mark) VALUES (%s, %s, %s, NOW(), '', %s)",
            (title, artist, tags, mark))
        db.commit()
        bot.send_message(message.chat.id, f"Музыкальное произведение '{title}' успешно добавлено!")
    except mysql.connector.errors.IntegrityError as e:
        bot.send_message(message.chat.id, f"Музыкальное произведение '{title}' уже есть в БД")
    except mysql.connector.errors.DatabaseError as e:
        logger.error(e)
        # if e.errno == 4031:  # mysql.connector.errors.DatabaseError: 4031 (HY000):
        #     if try_count < 2:
        #         connect_if_need()
        #         add_to_database(message, title, artist, tags, try_count=try_count + 1)
        #     else:
        #         print(e)
    except ValueError as e:
        logger.error(e)
        # bot.send_message(message.chat.id, "Оценка должна быть числом от 0 до 5.")


# Команда /addcsv для добавления нескольких музыкальных произведений из CSV
@bot.message_handler(commands=['addcsv'])
def add_csv(message):
    if message.from_user.username == env.TELEGRAM_ADMIN_USERNAME:
        bot.send_message(message.chat.id, "Вставьте список мулькальных композиций в формате CSV:")
        bot.register_next_step_handler(message, insert_csv)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")


def insert_csv(message):
    if message.from_user.username == env.TELEGRAM_ADMIN_USERNAME:
        music_data = message.text.split("\n")
        logger.info("Получено CSV-сообщение с " + str(len(music_data)) + " композиций")
        count_success, count_duplicates, count_dberror, count_error = 0, 0, 0, 0
        connect_if_need()
        for data in music_data:
            try:
                title, artist, tags = re.split(";", data)
                logger.info(f"Добавляется: {artist}, {title}, {tags}")
                cursor.execute(
                    "INSERT INTO repertuar (title, artist, tags) VALUES (%s, %s, %s)",
                    (title, artist, tags))
                db.commit()
                count_success += 1
            except mysql.connector.errors.IntegrityError as e:
                logger.error(e)
                count_duplicates += 1
            except mysql.connector.errors.DatabaseError as e:
                logger.error(e)
                count_dberror += 1
            except Exception as e:
                logger.error(e)
                count_error += 1

        if count_duplicates == 0 and count_error == 0:
            bot.send_message(message.chat.id, f"Музыкальные композиции успешно добавлены ({count_success} шт)")
        elif count_success > 0:
            bot.send_message(message.chat.id, f"Музыкальные композиции успешно добавлены ({count_success} шт)\n"
                                              f"Дубликатов - {count_duplicates} шт\n"
                                              f"Ошибок с БД - {count_dberror} шт\n"
                                              f"Прочих ошибок - {count_error} шт")
        else:
            bot.send_message(message.chat.id, f"Музыкальные композиции не были добавлены:\n"
                                              f"Дубликатов - {count_duplicates} шт\n"
                                              f"Ошибок с БД - {count_dberror} шт\n"
                                              f"Прочих ошибок - {count_error} шт")
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")


# Команда /random для получения случайного музыкального произведения
@bot.message_handler(commands=['random'])
def random_music(message):
    connect_if_need()
    try:
        cursor.execute("SELECT id, title, artist FROM repertuar ORDER BY RAND() LIMIT 1")
        result = cursor.fetchone()
        if result is not None:
            id, title, artist = result
    except mysql.connector.errors.DatabaseError as e:
        if e.errno == 4031:  # mysql.connector.errors.DatabaseError: 4031 (HY000):
            connect_if_need()

    if result is None:
        bot.send_message(message.chat.id, "Нет композиций в базе данных")
        return

    if message.from_user.username == env.TELEGRAM_ADMIN_USERNAME:
        markup = types.InlineKeyboardMarkup(row_width=6)
        buttons = [types.InlineKeyboardButton(mark, callback_data=f"update_rating_{id}_{mark}")
                   for mark in "012345"]
        markup.add(*buttons)

        bot.send_message(message.chat.id, f"{artist} - {title}",
                         reply_markup=markup)
    #        bot.register_next_step_handler(message, update_rating, result[0])
    else:
        bot.send_message(message.chat.id, f"{artist} - {title}")


def update_rating(message, repertuar_id, mark):
    connect_if_need()
    try:
        cursor.execute("UPDATE repertuar SET mark = %s, open_time = NOW() WHERE id = %s", (mark, repertuar_id))
        rows_updated = cursor.rowcount
        db.commit()

        if rows_updated == 1:
            bot.send_message(message.chat.id, "Оценка успешно сохранена!")
        else:
            bot.send_message(message.chat.id, "Композиция не найдена в базе данных")
    except Exception as e:
        logger.error(e)
        bot.send_message(message.chat.id, "Не удалось сохранить оценку, смотрите логи")


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("update_rating_"):
        id, mark = re.findall(r"\d+", call.data)
        update_rating(call.message, int(id), int(mark))


# Запуск бота
bot.polling()
