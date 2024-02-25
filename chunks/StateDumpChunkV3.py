import io
from sections.BaseV3 import TraceV3Chunk


class StateDump(TraceV3Chunk):
    def __init__(self, fd: io.BufferedReader):
        super().__init__(fd)
                
    def print_v3(self):
        pass
