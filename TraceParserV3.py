from HeaderChunkV3 import *
from CatalogChunkV3 import *
from ChunkSetChunkV3 import *
from BaseV3 import *
from pathlib import Path
from typing import Callable
import Globals


class TraceV3Parser:
    def __init__(self, tracev3_path: str):
        self.path = Path(tracev3_path)
        self.file_size = self.get_file_size()
        self.fd = self.try_open_trace_file()
        self.offset = 0

    def get_file_size(self):
        return self.path.stat().st_size

    def try_open_trace_file(self):
        fd = self.path.open("rb")
        if not fd:
            raise FileNotFoundError("File could not be opened !")
        return fd

    def update_offset_and_seek(self, chunk: TraceV3Chunk):
        self.offset += chunk.total_chunk_size
        self.fd.seek(self.offset)

    @staticmethod
    def parse_v3_chunk(constructor: Callable, *args):
        v3_obj = constructor(*args)
        return v3_obj

    def parse_v3_chunks(self):
        header_chunk = self.parse_v3_chunk(HeaderChunk, *[self.fd])
        self.update_offset_and_seek(header_chunk)
        Globals.catalog = self.parse_v3_chunk(CatalogChunk, *[self.fd])
        sub_chunks = Globals.catalog.get_sub_chunks()
        for sub_chunk in sub_chunks:
            Globals.chunk_sets.append(self.parse_v3_chunk(ChunkSet, *[self.fd, sub_chunk.uncompressed_data_size]))
