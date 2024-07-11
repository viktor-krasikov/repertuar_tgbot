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
    def add_song(self, title, artist, tags, mark):
        ...

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
