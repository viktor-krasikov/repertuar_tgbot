from dataclasses import dataclass
from typing import List
from abc import ABCMeta, abstractmethod, abstractproperty

@dataclass(init=True)
class Song:
    id: int
    title: str
    artist: str
    tags: str #List[str]
    mark: int


class StorageManager:
    __metaclass__ = ABCMeta

    @abstractmethod
    def add_song(self, title, artist, tags, mark) -> int:
        """Добавление композиции в БД
        Результат:
        0 - успешное добавление
        1 - попытка добавления дубля
        2 - ошибки, связанная с БД
        99 - прочие ошибки
        """

    @abstractmethod
    def get_songs_count(self) -> int:
        """Функция для получения количества музыкальных композиций"""

    @abstractmethod
    def get_tags(self) -> List[str]:
        """Функция для получения списка тегов"""

    @abstractmethod
    def get_random_song(self) -> Song:
        ...

    @abstractmethod
    def update_rating(self, song_id, rating):
        ...

    @abstractmethod
    def backup(self, file_path):
        """Выгрузка всех композиций в CSV файл."""
