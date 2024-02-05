import io
from BaseV3 import TraceV3Chunk


class OversizeChunk(TraceV3Chunk):
    def __init__(self, fd: io.BufferedReader):
        super().__init__(fd)

    def print_v3(self):
        pass
