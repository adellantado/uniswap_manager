from abc import ABC, abstractmethod


class Cachable(ABC):

    @abstractmethod
    def get_hash(self):
        pass