import uuid

from ProcV3 import *
from SubChunkV3 import *

class CatalogChunk(TraceV3Chunk):
    def __init__(self, tracev3_fd: io.BufferedReader):
        super().__init__(tracev3_fd)
        self.subsystem_strings_offset: int = self.read_subsystem_strings_offset()
        self.num_of_uuids: int = self.subsystem_strings_offset // 16
        self.process_info_offset: int = self.read_process_information_offset()
        self.num_of_proc: int = self.read_number_of_processes()
        self.sub_chunks_offset: int = self.read_sub_chunks_offset()
        self.num_of_sub_chunks: int = self.read_number_of_sub_chunks()
        self.read_padding()
        self.firehose_first_timestamp: int = self.read_earliest_firehose_timestamp()
        self.uuid_section_offset_global: int = self.fd.tell()
        self.subsystem_section_offset_global: int = self.uuid_section_offset_global + self.subsystem_strings_offset
        self.process_section_offset_global: int = self.uuid_section_offset_global + self.process_info_offset
        self.uuid_arr: list = self.read_uuid_array()
        self.subsystems: list = self.read_subsystem_strings()
        self.procs: dict = self.read_proc_info()
        self.sub_chunks: list = self.read_catalog_sub_chunks()

    def get_sub_chunks(self):
        return self.sub_chunks

    def get_num_of_sub_chunks(self):
        return len(self.sub_chunks)

    def read_subsystem_strings_offset(self):
        return struct.unpack("<H", self.fd.read(CATALOG_CHUNK_SUBSYSTEM_STRINGS_SIZE))[0]

    def read_process_information_offset(self):
        return struct.unpack("<H", self.fd.read(CATALOG_CHUNK_PROCESS_INFO_SIZE))[0]

    def read_number_of_processes(self):
        return struct.unpack("<H", self.fd.read(CATALOG_CHUNK_NUMBER_OF_PROCESS_INFO_SIZE))[0]

    def read_sub_chunks_offset(self):
        return struct.unpack("<H", self.fd.read(CATALOG_CHUNK_SUB_CHUNK_OFF_SIZE))[0]

    def read_number_of_sub_chunks(self):
        return struct.unpack("<H", self.fd.read(CATALOG_CHUNK_SUB_CHUNK_NUMBER_SIZE))[0]

    def read_padding(self):
        self.fd.read(CATALOG_CHUNK_SUB_CHUNK_PADDING_SIZE)

    def read_earliest_firehose_timestamp(self):
        return struct.unpack("<Q", self.fd.read(CATALOG_CHUNK_EARLIEST_FIREHOSE_TIMESTAMP_SIZE))[0]

    def read_uuid_array(self):
        uuids = list()
        for i in range(self.subsystem_strings_offset // 16):
            current_uuid = self.fd.read(CATALOG_CHUNK_UUID_SIZE).hex()
            uuids.append(uuid.UUID(current_uuid))
        return uuids

    def read_subsystem_strings(self):
        subsystems = list()
        while self.fd.tell() < self.process_section_offset_global:
            current_subsystem_str = ""
            current_letter = struct.unpack("<B", self.fd.read(1))[0]
            while current_letter != 0x0 and self.fd.tell() < self.process_section_offset_global:
                current_subsystem_str += chr(current_letter)
                current_letter = struct.unpack("<B", self.fd.read(1))[0]
            if len(current_subsystem_str):
                subsystems.append(current_subsystem_str)
        return subsystems

    def read_proc_info(self):
        self.fd.seek(self.process_section_offset_global)
        procs = dict()
        # proc member "entry id" is decremented rather than incremented
        for i in range(self.num_of_proc):
            proc = ProcInfo(self.fd, self.uuid_section_offset_global, self.num_of_uuids,
                            self.subsystem_section_offset_global)
            procs[proc.proc_id] = proc
        return procs

    def read_catalog_sub_chunks(self):
        sub_chunks = list()
        for i in range(self.num_of_sub_chunks):
            sub_chunk = SubChunk(self.fd, list(self.procs.values()), self.process_section_offset_global,
                                 self.subsystem_section_offset_global)
            sub_chunks.append(sub_chunk)
        return sub_chunks

    def print_v3(self):
        super().print_v3()
