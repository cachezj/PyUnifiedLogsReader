from sections.BaseV3 import GenericTraceV3ChunkSection
from util.utils import *

class SubChunk(GenericTraceV3ChunkSection):
    def __init__(self, tracev3_fd: io.BufferedReader, procs: list, process_section_offset_global: int, subsystem_strings_offset_globl: int):
        super().__init__(tracev3_fd)
        self.proc_info_offset_global = process_section_offset_global
        self.procs_global = procs
        self.num_of_procs_global = len(procs)
        self.subsystem_strings_offset_global = subsystem_strings_offset_globl

        self.start_time = self.read_start_time()
        self.end_time = self.read_end_time()
        self.uncompressed_data_size = self.read_uncompressed_data_size()
        self.algo = self.read_algo_type()
        self.num_of_procs = self.read_num_of_proc()
        self.procs_in_sub_chunk = self.read_procs()
        self.num_of_string_offsets = self.read_num_of_string_offsets()
        self.sub_chunk_subsystem_strings = self.read_strings()
        self.align_cursor()

    def read_start_time(self):
        return struct.unpack("<Q", self.fd.read(CATALOG_CHUNK_SUB_CHUNK_START_TIME_SIZE))[0]

    def read_end_time(self):
        return struct.unpack("<Q", self.fd.read(CATALOG_CHUNK_SUB_CHUNK_END_TIME_SIZE))[0]

    def read_algo_type(self):
        return struct.unpack("<I", self.fd.read(CATALOG_CHUNK_SUB_CHUNK_ALGO_SIZE))[0]

    def read_uncompressed_data_size(self):
        return struct.unpack("<I", self.fd.read(CATALOG_CHUNK_SUB_CHUNK_UNCOMPRESSED_DATA_SIZE_SIZE))[0]

    def read_num_of_proc(self):
        return struct.unpack("<I", self.fd.read(CATALOG_CHUNK_SUB_CHUNK_PROC_NUM_SIZE))[0]

    def read_procs(self):
        procs = list()
        for i in range(self.num_of_procs):
            proc_index = struct.unpack("<H", self.fd.read(CATALOG_CHUNK_SUB_CHUNK_PROC_INDEX_SIZE))[0]
            if proc_index > self.num_of_procs_global:
                raise ValueError("invalid proc index")
            procs.append(self.procs_global[proc_index])
        return procs

    def read_num_of_string_offsets(self):
        return struct.unpack("<I", self.fd.read(CATALOG_CHUNK_SUB_CHUNK_NUM_OF_STRINGS_SIZE))[0]

    def read_strings(self):
        subsystem_strings = list()
        for i in range(self.num_of_string_offsets):
            current_offset = struct.unpack("<H", self.fd.read(CATALOG_CHUNK_SUB_CHUNK_STRING_OFFSET_SIZE))[0]
            if current_offset + self.subsystem_strings_offset_global > self.proc_info_offset_global:
                raise ValueError("invalid subsystem string offset")
            current_subsystem_str = read_and_return_to_cursor(self.fd, self.subsystem_strings_offset_global + current_offset, 0)
            subsystem_strings.append(current_subsystem_str)
        return subsystem_strings

    def print_procs(self):
        for proc in self.procs_in_sub_chunk:
            proc.print()

    def print_v3(self):
        print(f"""
            start time: {self.start_time}
            end time: {self.end_time}
            uncompressed data size: {self.uncompressed_data_size}
            compression algo: {self.algo}
            subsystems: {self.sub_chunk_subsystem_strings}
            procs: 
        """)
        self.print_procs()
