from abc import *
from utils.utils import *


class GenericTraceV3ChunkSection(ABC):
    def __init__(self, tracev3_fd: io.BufferedReader):
        self.fd = tracev3_fd
        self.chunk_start = self.fd.tell()
        # print(f"Current cursor offset {self.fd.tell()}")

    def align_cursor(self):
        if self.fd.tell() % 8 != 0:
            # print(f"{hex(self.fd.tell())} <-> {hex(self.fd.tell() + 8 - ((self.fd.tell() + 8) % 8))}")
            return self.fd.seek(self.fd.tell() + 8 - ((self.fd.tell() + 8) % 8))

    @abstractmethod
    def print_v3(self):
        pass

    def json(self):
        pass


chunk_number = 1


class TraceV3Chunk(GenericTraceV3ChunkSection):
    def __init__(self, tracev3_fd: io.BufferedReader):
        global chunk_number
        super().__init__(tracev3_fd)
        self.chunk_number = chunk_number
        self.chunk_start = self.fd.tell()
        self.tag = self.parse_tag()
        self.sub_tag = self.parse_subtag()
        self.data_size = self.parse_data_size()
        self.total_chunk_size = self.data_size + CHUNK_DATA_SIZE_SIZE + CHUNK_SUB_TAG_SIZE + CHUNK_TAG_SIZE
        self.type = self.get_chunk_type()
        chunk_number += 1

    def parse_tag(self):
        return hex(struct.unpack("<I", self.fd.read(CHUNK_TAG_SIZE))[0])

    def parse_subtag(self):
        return hex(struct.unpack("<I", self.fd.read(CHUNK_SUB_TAG_SIZE))[0])

    def parse_data_size(self):
        return int(struct.unpack("<Q", self.fd.read(CHUNK_DATA_SIZE_SIZE))[0])

    def read_raw_data(self):
        return self.fd.read(self.data_size)

    def get_chunk_type(self):
        if self.tag in chunk_types.keys():
            return chunk_types[self.tag]

    def parse(self):
        yield self
        return
    @abstractmethod
    def print_v3(self):
        print(f"tag = {self.tag}")
        print(f"subtag = {self.sub_tag}")
        print(f"chunk data size = {self.data_size}")
        print(f"chunk size = {self.total_chunk_size}")