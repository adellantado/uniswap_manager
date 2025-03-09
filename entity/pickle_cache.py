from __future__ import annotations
import pickle
import os


class PickleCache():

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