from sections.BaseV3 import *
from utils import *

class FirehoseChunk(TraceV3Chunk):
    def __init__(self, tracev3_fd: io.BufferedReader):
        super().__init__(tracev3_fd)
        self.proc_id: str = self.read_proc_id()
        self.ttl: int = self.read_ttl()
        self.is_collapsed: int = self.read_collapsed()
        self.read_unknown()
        self.public_firehose_data_size: int = self.read_public_data_size()
        self.private_data_virtual_offset: int = self.read_private_data_virtual_offset()
        self.has_private_data = self.private_data_virtual_offset != 4096
        self.private_data_size = 4096 - self.private_data_virtual_offset
        self.firehose_trace_points_size: int = self.data_size - self.private_data_size - 32
        self.read_unknown_2nd()
        self.stream_type: str = self.read_stream_type()
        self.read_unknown_3rd()
        self.continuous_time: int = self.read_base_mach_time()
        self.trace_point_offset = self.fd.tell()
        self.private_data_real_offset: int = self.trace_point_offset + self.firehose_trace_points_size
        self.firehose_end: int = self.private_data_real_offset + self.private_data_size
        if self.has_private_data:
            self.private_data: str = self.read_private_data()
        else:
            self.private_data = None

    def read_private_data(self):
        self.fd.seek(self.private_data_real_offset)
        return utils.read_null_terminated_string_from_fd(self.fd, self.private_data_size)

    def read_proc_id(self):
        return read_proc_id(self.fd)

    def read_ttl(self):
        return struct.unpack("<B", self.fd.read(SIMPLE_DUMP_CHUNK_TTL_SIZE))[0]

    def read_collapsed(self):
        return struct.unpack("<B", self.fd.read(FIREHOSE_CHUNK_COLLAPSED_SIZE))[0]

    def read_unknown(self):
        return struct.unpack("<H", self.fd.read(FIREHOSE_CHUNK_UNKNOWN_1ST_SIZE))[0]

    def read_public_data_size(self):
        return struct.unpack("<H", self.fd.read(FIREHOSE_CHUNK_PUBLIC_DATA_SIZE))[0]

    def read_private_data_virtual_offset(self):
        return struct.unpack("<H", self.fd.read(FIREHOSE_CHUNK_PRIVATE_DATA_VIRTUAL_OFFSET_SIZE))[0]

    def read_unknown_2nd(self):
        return struct.unpack("<H", self.fd.read(FIREHOSE_CHUNK_UNKNOWN_2ND_SIZE))[0]

    def read_stream_type(self):
        s_type = struct.unpack("<B", self.fd.read(FIREHOSE_CHUNK_COLLAPSED_SIZE))[0]
        if s_type not in stream_types.keys():
            raise ValueError("stream type isn't valid")
        return stream_types[s_type]

    def read_unknown_3rd(self):
        return struct.unpack("<B", self.fd.read(FIREHOSE_CHUNK_UNKNOWN_3RD_SIZE))[0]

    def read_base_mach_time(self):
        return struct.unpack("<Q", self.fd.read(FIREHOSE_CHUNK_BASE_CONTINUOUS_TIME_SIZE))[0]

    def read_trace_points(self):
        from TracepointV3 import trace_point_log_type_ctors
        trace_points_start = self.fd.tell()
        # print(f"{trace_points_start}")
        i = 1
        while self.fd.tell() < trace_points_start + self.firehose_trace_points_size:
            record_type = struct.unpack("<B",
                                        read_and_return_to_cursor(self.fd, self.fd.tell(),
                                                                  FIREHOSE_TRACE_POINT_RECORD_TYPE_SIZE))[0]
            if record_type not in firehose_trace_point_record_types:
                raise ValueError("bad record type")

            point = trace_point_log_type_ctors[record_type](self.fd, self)
            # point.print_v3()
            yield point
            i += 1

    def parse(self):
        self.fd.seek(self.trace_point_offset)
        yield from self.read_trace_points()
        if self.has_private_data:
            self.fd.seek(self.firehose_end)
        self.align_cursor()

    def print_v3(self):
        print(f"""
        proc_id: {self.proc_id}
        ttl: {self.ttl}
        collapsed: {self.is_collapsed}
        public data size: {self.public_firehose_data_size}
        private virtual offset: {self.private_data_virtual_offset}
        stream type: {self.stream_type}
        base time: {self.continuous_time}""")

