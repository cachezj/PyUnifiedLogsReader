from base_struct import Struct


class Header(Struct):

    @staticmethod
    def _fmt() -> str:
        return "<IIII"

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
    def ranges_count(self):
        return self._values[3]


class TextEntryDescriptor(Struct):

    @staticmethod
    def _fmt() -> str:
        return "<II"

    @property
    def range_offset(self):
        return self._values[0]

    @property
    def data_size(self):
        return self._values[1]
