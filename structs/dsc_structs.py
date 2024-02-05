import uuid

from base_struct import Struct


class Header(Struct):

    @staticmethod
    def _fmt() -> str:
        return "<4sHHII"

    @property
    def cigam(self):
        return self._values[0]

    @property
    def major(self):
        return self._values[1]

    @property
    def minor(self):
        return self._values[2]

    @property
    def range_count(self):
        return self._values[3]

    @property
    def uuid_count(self):
        return self._values[4]


class StringRangeDescriptor(Struct):

    @staticmethod
    def _fmt() -> str:
        return "<QIIQ"

    @property
    def range_offset(self):
        return self._values[0]

    @property
    def data_offset(self):
        return self._values[1]

    @property
    def range_size(self):
        return self._values[2]

    @property
    def uuid_index(self):
        return self._values[3]


class StringUUIDDescriptor(Struct):
    @staticmethod
    def _fmt() -> str:
        return "<QIQQI"

    @property
    def text_offset(self):
        return self._values[0]

    @property
    def text_size(self):
        return self._values[1]

    @property
    def uuid(self):
        return uuid.UUID(int=self._switch_endianness("<Q", self._values[2]) << 64 |
                             self._switch_endianness("<Q", self._values[3]))

    @property
    def path_offset(self):
        return self._values[4]

    # @property
    #     def (self):
    #         return self._values[]
