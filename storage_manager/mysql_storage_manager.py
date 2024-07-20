import csv

import mysql.connector

from storage_manager import Song, StorageManager


class MysqlStorageManager(StorageManager):

    def __init__(self, logger, mysql_connection_params):
        self.logger = logger
        self.connection_params = mysql_connection_params
        self.db = None
        self.cursor = None
        self.connect_if_need()
        # Создание таблицы 'repertuar', если её нет
        self.cursor.execute("""
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

    def __deinit__(self):
        self.cursor.close()
        self.db.close()

    # Функция для проверки  соединения
    def is_connected(self):
        if self.db is not None and self.cursor is not None:
            try:
                self.cursor.execute("SELECT 1")
                result = self.cursor.fetchone()
                if result is not None:
                    return True
            except mysql.connector.Error as e:
                self.logger.error(f"Error checking connection: {e}")
            except Exception as e:
                self.logger.error(f"Unknown error in is_connected: {e}")
        return False

    # Подключение к базе данных MySQL
    def connect_if_need(self):
        if not self.is_connected():
            self.logger.info("Попытка соединения с БД")
            self.db = mysql.connector.connect(**self.connection_params)
            self.cursor = self.db.cursor()
            self.logger.info("Соединение с БД установлено")

    def get_songs_count(self):
        self.connect_if_need()
        self.cursor.execute("SELECT COUNT(*) FROM repertuar")
        return self.cursor.fetchone()[0]

    def get_tags(self):
        self.connect_if_need()
        self.cursor.execute("""
            SELECT DISTINCT tag
            FROM repertuar,
                JSON_TABLE(
                    CONCAT('["', REPLACE(tags, ',', '","'), '"]'),
                    "$[*]" COLUMNS(
                        tag VARCHAR(255) PATH "$"
                    )
                ) AS tags;
        """)
        tag_list = ', '.join([row[0] for row in self.cursor.fetchall()])
        return tag_list

    def get_random_song(self) -> Song:
        self.connect_if_need()
        try:
            self.cursor.execute("SELECT id, title, artist, tags, mark FROM repertuar ORDER BY RAND() LIMIT 1")
            result = self.cursor.fetchone()
            if result is not None:
                id, title, artist, tags, mark = result
                return Song(id, title, artist, tags, mark)

        except mysql.connector.errors.DatabaseError as e:
            if e.errno == 4031:  # mysql.connector.errors.DatabaseError: 4031 (HY000):
                self.connect_if_need()

    def update_rating(self, song_id, mark):
        self.connect_if_need()
        self.cursor.execute("UPDATE repertuar SET mark = %s, open_time = NOW() WHERE id = %s", (mark, song_id))
        rows_updated = self.cursor.rowcount
        self.db.commit()
        return rows_updated

    def add_song(self, title, artist, tags, mark=0):
        try:
            self.connect_if_need()
            self.cursor.execute(
                "INSERT INTO repertuar (title, artist, tags, mark) VALUES (%s, %s, %s, %s)",
                (title, artist, tags, mark))
            self.db.commit()
            return 0
        except mysql.connector.errors.IntegrityError as e:
            self.logger.error(e)
            return 1  # дубль
        except mysql.connector.errors.DatabaseError as e:
            self.logger.error(e)
            return 2
        except Exception as e:
            self.logger.error(e)
        return 99


def backup(self, file_path):
    """Выгрузка всех композиций в CSV файл."""
    self.connect_if_need()
    self.cursor.execute("SELECT title, artist, tags, mark FROM repertuar")
    rows = self.cursor.fetchall()

    # Запись данных в CSV файл
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';')  # Используем точку с запятой в качестве разделителя
        # Запись данных
        for row in rows:
            writer.writerow(row)

    self.logger.info(f"Бэкап завершён. Файл сохранен по пути: {file_path}")
    return file_path
