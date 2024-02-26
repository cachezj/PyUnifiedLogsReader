from sections.BaseV3 import *
from utils import *
from chunk_v3.firehose_structs import Metadata
class FirehoseChunk(TraceV3Chunk):
    def __init__(self, tracev3_fd: io.BufferedReader):
        super().__init__(tracev3_fd)
        self.metadata = Metadata(self.fd.read(Metadata.size()))
        # self.has_private_data = self.private_data_virtual_offset != 4096
        # self.private_data_size = 4096 - self.private_data_virtual_offset
        self.trace_point_offset = self.fd.tell()
        # self.private_data_real_offset: int = self.trace_point_offset + self.firehose_trace_points_size
        # self.firehose_end: int = self.private_data_real_offset + self.private_data_size
        # if self.has_private_data:
        #     self.private_data: str = self.read_private_data()
        # else:
        #     self.private_data = None

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

