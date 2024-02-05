from SimpleDumpChunkV3 import *
from FirehoseChunkV3 import *
from StateDumpChunkV3 import *
from HeaderChunkV3 import *
from OversizeChunkV3 import *

ctors_by_chunk_type = {"SimpleDump": SimpleDump, "Firehose": FirehoseChunk, "Header": HeaderChunk,
                       "Oversize": OversizeChunk, "StateDump": StateDump}

class ChunkSet(TraceV3Chunk):
    def __init__(self, tracev3_fd: io.BufferedReader, uncompressed_data_size: int):
        super().__init__(tracev3_fd)
        self.uncompressed_data_size_from_sub_chunk: int = uncompressed_data_size
        self.compressed_data_size: int = self.data_size
        self.chunks: list = self.parse_chunks()
        self.align_cursor()

    def print_v3(self):
        super().print_v3()

    def parse_chunks(self):
        chunks = list()
        chunks_buf = self.read_lz4_block()
        # with open("chunks.test.dec", 'wb') as chunks_file:
        #     chunks_file.write(chunks_buf)
        reader = io.BufferedReader(io.BytesIO(chunks_buf))
        while reader.tell() != self.uncompressed_data_size_from_sub_chunk:
            print(f"{reader.tell()}")
            chunk_type = read_and_return_to_cursor(reader, reader.tell(), 4)
            chunk_type = struct.unpack("<I", chunk_type)[0]
            if len(chunks) > 0 and chunks[-1].chunk_number == 44:
                print(f"{hex(reader.tell())}")
            if chunk_type not in chunk_types.keys():
                print(f"{hex(reader.tell())}")
                raise ValueError("Unknown chunk type")
            chunk_type_human_readable = chunk_types[chunk_type]
            chunk: TraceV3Chunk = ctors_by_chunk_type[chunk_type_human_readable](reader)
            chunks.append(chunk)
            chunk.print_v3()

        reader.close()
        return chunks

    def read_lz4_block(self):
        start_magic = self.fd.read(CHUNK_SET_LZ4_START_MAGIC_SIZE)
        if start_magic == CHUNK_SET_START_MAGIC_COMPRESSED:
            return self.read_and_decompress_chunks()
        if start_magic == CHUNK_SET_START_MAGIC_DECOMPRESSED:
            return self.read_uncompressed_data()
        raise ValueError("Invalid lz4 block marker")

    def read_uncompressed_data(self):
        uncompressed_size = struct.unpack("<I", self.fd.read(CHUNK_SET_LZ4_DECOMPRESSED_DATA_SIZE))[0]
        if uncompressed_size != self.uncompressed_data_size_from_sub_chunk:
            raise ValueError("uncompressed size is not equal to the size state in the sub chunk")
        return self.fd.read(uncompressed_size)

    def read_and_decompress_chunks(self):
        uncompressed_size = struct.unpack("<I", self.fd.read(CHUNK_SET_LZ4_DECOMPRESSED_DATA_SIZE))[0]
        if uncompressed_size != self.uncompressed_data_size_from_sub_chunk:
            raise ValueError("Invalid uncompressed data size in chunk set")
        compressed_size = struct.unpack("<I", self.fd.read(CHUNK_SET_LZ4_COMPRESSED_DATA_SIZE))[0]
        compressed_data = self.fd.read(compressed_size)
        print(hex(self.fd.tell()))
        # with open("test.lz4", 'wb') as lz4_file:
        #     lz4_file.write(compressed_data)
        end_magic = self.fd.read(CHUNK_SET_LZ4_END_MAGIC_SIZE)
        if end_magic != CHUNK_SET_END_MAGIC:
            raise ValueError("Invalid lz4 end magic in chunk set")
        decompressed_data = decompress_lz4_buffer(compressed_data, self.uncompressed_data_size_from_sub_chunk)
        if len(decompressed_data) != self.uncompressed_data_size_from_sub_chunk:
            raise ValueError("Bad decompressed buffer length")
        return decompressed_data

