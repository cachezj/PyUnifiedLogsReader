from chunks.CatalogChunkV3 import *
from chunks.ChunkSetChunkV3 import *
from sections.BaseV3 import *
from pathlib import Path
from util import Globals


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

    def parse_v3_chunks(self):
        header_chunk = HeaderChunk(self.fd)
        self.update_offset_and_seek(header_chunk)
        Globals.catalog = CatalogChunk(self.fd)
        sub_chunks = Globals.catalog.get_sub_chunks()
        for sub_chunk in sub_chunks:
            chunk_set = ChunkSet(self.fd, sub_chunk.uncompressed_data_size)
            for chunk in chunk_set.parse_chunks():
                chunk.print_v3()