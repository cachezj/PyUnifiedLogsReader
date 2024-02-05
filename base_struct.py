import struct
from abc import ABC, abstractmethod


class Struct(ABC):
    _values: [] = None

    def __init__(self, data: bytes):
        self._values = struct.unpack(self._fmt(), data)

    @staticmethod
    @abstractmethod
    def _fmt() -> str:
        pass

    @classmethod
    def size(cls):
        return struct.calcsize(cls._fmt())

    def _switch_endianness(self, fmt: str, value: int):
        packed_data = struct.pack(fmt, value)
        fmt = fmt.replace("<", ">") if "<" in fmt else fmt.replace(">", "<")
        return struct.unpack(fmt, packed_data)[0]