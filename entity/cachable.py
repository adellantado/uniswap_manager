from abc import ABC, abstractmethod


class Cachable(ABC):
    """
    Abstract base class that defines a contract for cachable entities.

    Methods:
        get_hash(): Abstract method that should be implemented to return a unique hash for the cachable entity.
    """

    @abstractmethod
    def get_hash(self):
        pass