import io
import uuid
from typing import Union, Tuple
from pathlib import Path

from accessories.base_file import BaseFile
from structs.uuid_structs import *


class UuidText(BaseFile):
    SUPPORTED_VERSION = "2.1"
    CIGAM = 0x66778899
    entries: list[Tuple[int, TextEntryDescriptor]] = []  # [range offset, data size]

    header: Header = None

    def __parse_header(self):
        self.header = Header(self.file.read(Header.size()))
        if self.header.cigam != self.CIGAM:
            raise ValueError("File entered is not Uuid Text")
        version = f"{self.header.major:d}.{self.header.minor:d}"
        if version != self.SUPPORTED_VERSION:
            raise ValueError(f"Unsupported version: {version}, got {self.SUPPORTED_VERSION}")

    def __read_entries(self):
        entries = []
        if not self.header.ranges_count:
            return
        for _ in range(self.header.ranges_count):
            entry = TextEntryDescriptor(self.file.read(TextEntryDescriptor.size()))
            entries.append(entry)
        file_offset = self.file.tell()
        for entry in entries:
            self.entries.append((file_offset, entry))
            file_offset += entry.data_size

    def _read_footer(self):
        # get the offset of the last entry and add its size
        footer_offset = self.entries[-1][0] + self.entries[-1][1].data_size if self.header.ranges_count\
            else self.file.tell()
        self.footer, end_footer = self._read_string(footer_offset)
        self.file.seek(end_footer, io.SEEK_SET)

    def read_string_reference(self, string_reference: int) -> Union[str, Tuple[str, uuid.UUID, Path], None]:
        """:arg string_reference [int] a 4 byte value

        reference in range of the entries
        if the MSB is on "%s" is returned"""

        if self._is_dynamic(string_reference):
            return "%s"

        for file_offset, entry in self.entries:
            if string_reference < entry.range_offset:
                continue
            relative_offset = string_reference - entry.range_offset
            if relative_offset <= entry.data_size:  # check if the offset is less then the size of the range
                real_string_reference = file_offset + relative_offset
                return self._read_string(real_string_reference)[0]
        return None

    def parse(self):
        self.__parse_header()
        self.__read_entries()
        self._read_footer()
        return self


# if __name__ == '__main__':
#     a = UuidText(Path("/Users/messi/Desktop/system_logs.logarchive/6A/3F527081F03228BD1170E1D0613C76"))
#     a.parse()
#     print(a.footer)
#     print(a.read_string_reference(277138))
