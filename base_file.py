import io
import uuid
from abc import ABC, abstractmethod
from typing import Union, Tuple, BinaryIO
from pathlib import Path

import uuid_text

BASE_DIR: Path


class BaseFile(ABC):
    file: BinaryIO = None
    footer: str = None

    def __init__(self, file: Union[Path, io.FileIO, str, uuid.UUID]):
        if isinstance(file, Path):
            self.file = file.open("rb")
            return

        if isinstance(file, io.FileIO):
            self.file = file
            return

        if isinstance(file, uuid.UUID):
            file = file.hex

        if isinstance(self, uuid_text.UuidText):
            file_name = BASE_DIR / file[0:2] / file[2:]
        else:
            file_name = BASE_DIR/"dsc"/file

        self.file = file_name.open("rb")

    @abstractmethod
    def parse(self):
        pass

    def _read_string(self, offset: int) -> Tuple[str, int]:
        """does not move the cursor!!
        @:return tuple of the string and the offset of the next byte after the \x00"""
        string = ""
        pos = self.file.tell()
        self.file.seek(offset, io.SEEK_SET)
        while True:
            char: bytes = self.file.read(1)
            if char == b'':
                raise ValueError(f"invalid offset {offset}")
            if not char.isascii():
                raise ValueError(f"Not a valid cstring, got this byte {char:c}")
            if char == b"\0":
                break
            string += char.decode()
        self.file.seek(pos, io.SEEK_SET)
        return string, offset + len(string) + 1  # +1 to account for the terminating null

    @abstractmethod
    def read_string_reference(self, string_reference: int) -> Union[str, Tuple[str, uuid.UUID, Path], None]:
        """:arg string_reference [int] a 4 byte value

        reference in range of the entries
        if the MSB is on "%s" is returned"""
        pass

    @staticmethod
    def _is_dynamic(reference: int):
        return reference & (2 ** 32) != 0

    def __del__(self):
        if not self.file.closed:
            self.file.close()
