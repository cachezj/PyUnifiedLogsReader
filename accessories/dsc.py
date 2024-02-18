from typing import Union, Tuple
from pathlib import Path

from accessories.base_file import BaseFile
from structs.dsc_structs import *


class DSC(BaseFile):
    """Doesnt handle dsc version 1.0"""
    SUPPORTED_VERSIONS = ["2.0"]
    CIGAM = b'hcsd'
    header: Header = None
    ranges: list[StringRangeDescriptor] = []
    uuids: list[StringUUIDDescriptor] = []

    def __parse_header(self):
        self.header = Header(self.file.read(Header.size()))
        if self.header.cigam != self.CIGAM:
            raise ValueError("File entered is not Uuid Text")
        version = f"{self.header.major:d}.{self.header.minor:d}"
        if version not in self.SUPPORTED_VERSIONS:
            raise ValueError(f"Unsupported version: {version}, out of {self.SUPPORTED_VERSIONS}")

    def __read_ranges(self):
        for _ in range(self.header.range_count):
            self.ranges.append(StringRangeDescriptor(self.file.read(StringRangeDescriptor.size())))

    def __read_uuids(self):
        for _ in range(self.header.range_count):
            self.uuids.append(StringUUIDDescriptor(self.file.read(StringUUIDDescriptor.size())))

    def read_string_reference(self, string_reference: int) -> Union[str, Tuple[str, uuid.UUID, Path], None]:
        for dsc_range in self.ranges:
            dsc_uuid = self.uuids[dsc_range.uuid_index]
            if self._is_dynamic(string_reference):
                range_offset = dsc_uuid.text_offset
                range_size = dsc_uuid.text_size
            else:
                range_offset = dsc_range.range_offset
                range_size = dsc_range.range_size

            if string_reference < range_offset:
                continue

            relative_offset = string_reference - range_offset
            if relative_offset <= range_size:
                if self._is_dynamic(string_reference):
                    string = '%s'
                else:
                    file_offset = dsc_range.data_offset + relative_offset
                    string = self._read_string(file_offset)[0]
                return string, dsc_uuid.uuid, Path(self._read_string(dsc_uuid.path_offset)[0])
        return None

    def parse(self):
        self.__parse_header()
        self.__read_ranges()
        self.__read_uuids()
        return self


if __name__ == '__main__':
    a = DSC(Path("/Users/messi/Desktop/system_logs.logarchive/dsc/CB9BA1CB68AC32AAA8DE443E424C48D1"))
    a.parse()
