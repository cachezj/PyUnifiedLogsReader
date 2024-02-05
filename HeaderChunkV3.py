from BaseV3 import *


class HeaderChunk(TraceV3Chunk):
    def __init__(self, tracev3_fd: io.BufferedReader):
        super().__init__(tracev3_fd)

    def parse_data(self):
        pass

    def print_v3(self):
        super().print_v3()