from __future__ import annotations
import pickle
import os


class PickleCache():
    """
    A class used to manage caching using pickle serialization.

    Attributes
    ----------
    file_name : str
        The name of the file where the cache is stored.
    cache : dict
        The dictionary that holds the cached data.

    Methods
    -------
    has(key)
        Checks if the cache contains the given key.
    get(key)
        Retrieves the value associated with the given key from the cache.
    set(key, value)
        Sets the value for the given key in the cache and persists it.
    clear()
        Clears all the data in the cache.
    get_instance(name: str) -> PickleCache
        Returns a singleton instance of PickleCache for the given name.
    _fetch()
        Loads the cache from the pickle file if it exists.
    _persist()
        Persists the current cache to the pickle file.
    """

    _instances = {}

    def __init__(self, name: str):
        self.file_name = name
        self._fetch()

    def has(self, key):
        return key in self.cache

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value):
        self.cache[key] = value
        self._persist()

    def clear(self):
        self.cache.clear()

    @staticmethod
    def get_instance(name: str) -> PickleCache:
        if name not in PickleCache._instances:
            PickleCache._instances[name] = PickleCache(name)
        return PickleCache._instances[name]

    def _fetch(self):
        self.cache = {}
        if os.path.exists(f"cache/{self.file_name}.pkl"):
            with open(f"cache/{self.file_name}.pkl", "rb") as f:
                self.cache = pickle.load(f)

    def _persist(self):
        with open(f"cache/{self.file_name}.pkl", "wb") as f:
            pickle.dump(self.cache, f)