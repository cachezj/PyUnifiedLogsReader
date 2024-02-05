from BaseV3 import *
from uuid_text import UuidText


class SimpleDump(TraceV3Chunk):
    def __init__(self, tracev3_fd: io.BufferedReader):
        super().__init__(tracev3_fd)
        self.proc_id: str = self.read_proc_id()
        self.ttl: int = self.read_ttl()
        log_type: int = self.read_log_type()
        if log_type not in log_types.keys():
            raise ValueError("bad log type in SimpleDump")
        self.log_type = log_types[log_type]
        self.read_1st_unknown()
        self.timestamp: int = self.read_timestamp()
        self.tid: int = self.read_tid()
        self.load_addr: int = self.read_load_addr()
        self.sender_id: str = self.read_sender_image_uuid()
        self.sender_image_path: str = self.read_sender_image_path()
        self.dsc_id: uuid.UUID = self.read_dsc_uuid()
        self.read_2nd_unknown()
        self.subsystem_str_size: int = self.read_subsystem_str_size()
        self.message_str_size: int = self.read_message_str_size()
        self.subsystem_str = self.read_subsystem_string(self.subsystem_str_size)
        self.message_str = self.read_message_string(self.message_str_size)
        self.align_cursor()

    def read_sender_image_path(self):
        return UuidText(self.sender_id).parse().footer

    def read_proc_id(self):
        return read_proc_id(self.fd)

    def read_ttl(self):
        return struct.unpack("<B", self.fd.read(1))[0]

    def read_log_type(self):
        return struct.unpack("<B", self.fd.read(SIMPLE_DUMP_CHUNK_LOG_TYPE_SIZE))[0]

    def read_1st_unknown(self):
        self.fd.read(SIMPLE_DUMP_CHUNK_UNKNOWN_1ST_SIZE)

    def read_timestamp(self):
        return struct.unpack("<Q", self.fd.read(SIMPLE_DUMP_CHUNK_TIMESTAMP_SIZE))[0]

    def read_tid(self):
        return struct.unpack("<Q", self.fd.read(SIMPLE_DUMP_CHUNK_THREAD_ID_SIZE))[0]

    def read_load_addr(self):
        return struct.unpack("<Q", self.fd.read(SIMPLE_DUMP_CHUNK_LOAD_ADDR_SIZE))[0]

    def read_sender_image_uuid(self):
        return uuid.UUID(self.fd.read(CATALOG_CHUNK_UUID_SIZE).hex()).hex

    def read_dsc_uuid(self):
        return uuid.UUID(self.fd.read(CATALOG_CHUNK_UUID_SIZE).hex())

    def read_2nd_unknown(self):
        self.fd.read(SIMPLE_DUMP_CHUNK_UNKNOWN_2ND_SIZE)

    def read_subsystem_str_size(self):
        return struct.unpack("<I", self.fd.read(SIMPLE_DUMP_CHUNK_SUBSYSTEM_STRING_SIZE_SIZE))[0]

    def read_message_str_size(self):
        return struct.unpack("<I", self.fd.read(SIMPLE_DUMP_CHUNK_MESSAGE_STRING_SIZE_SIZE))[0]

    def read_subsystem_string(self, size):
        return read_null_terminated_string_from_fd(self.fd, size)

    def read_message_string(self, size):
        return read_null_terminated_string_from_fd(self.fd, size)

    def print_v3(self):
        pass
