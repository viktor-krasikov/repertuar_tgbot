from storage_manager import Song, StorageManager
import psycopg2


class PostgresqlStorageManager(StorageManager):

    def __init__(self, logger, postgresql_connection_params):
        self.logger = logger
        self.connection_params = postgresql_connection_params
        self.db = None
        self.cursor = None
        self.connect_if_need()
        # Создание таблицы 'repertuar', если её нет
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS repertuar (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                artist VARCHAR(255) NOT NULL,
                tags TEXT,
                open_time TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                content TEXT,
                mark INT DEFAULT 0,
                UNIQUE (title, artist)
            );
        """)

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
            except psycopg2.Error as e:
                self.logger.error(f"Error checking connection: {e}")
            except Exception as e:
                self.logger.error(f"Unknown error in is_connected: {e}")
        return False

    # Подключение к базе данных PostgreSQL
    def connect_if_need(self):
        if not self.is_connected():
            self.logger.info("Попытка соединения с БД")
            self.db = psycopg2.connect(**self.connection_params)
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
                unnest(string_to_array(tags, ',')) AS tag;
        """)
        tag_list = ', '.join([row[0] for row in self.cursor.fetchall()])
        return tag_list

    def get_random_song(self) -> Song:
        self.connect_if_need()
        self.cursor.execute("SELECT id, title, artist, tags, mark FROM repertuar ORDER BY RANDOM() LIMIT 1")
        result = self.cursor.fetchone()
        if result is not None:
            id, title, artist, tags, mark = result
            return Song(id, title, artist, tags, mark)

    def update_rating(self, song_id, mark):
        self.connect_if_need()
        self.cursor.execute("UPDATE repertuar SET mark = %s, open_time = NOW() WHERE id = %s", (mark, song_id))
        rows_updated = self.cursor.rowcount
        self.db.commit()
        return rows_updated

    def add_song(self, title, artist, tags, mark):
        self.connect_if_need()
        self.cursor.execute(
            "INSERT INTO repertuar (title, artist, tags, mark) VALUES (%s, %s, %s, %s)",
            (title, artist, tags, mark))
        self.db.commit()
