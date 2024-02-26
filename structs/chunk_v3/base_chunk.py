from base_struct import Struct
from abc import ABC

class Header(Struct):
    @staticmethod
    def _fmt() -> str:
        return "<QIB"

    @property
    def first_pid(self):
        return self._values[0]

    @property
    def second_pid(self):
        return self._values[1]

    @property
    def ttl(self):
        return self._values[2]