import Globals
import utils
from ProcV3 import ProcInfo
from BaseV3 import *
from utils import *
from accessories.uuid_text import UuidText
from accessories.dsc import DSC

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


class FirehoseTracePoint(GenericTraceV3ChunkSection):
    def __init__(self, tracev3_fd: io.BufferedReader, firehose_chunk: FirehoseChunk):
        super().__init__(tracev3_fd)
        self.firehose_main_chunk: FirehoseChunk = firehose_chunk
        self.proc_id: str = self.firehose_main_chunk.proc_id
        self.trace_point_private_data: list = list()
        self.sender_image_path: str = "N/A"
        self.sender_uuid: str = "N/A"
        self.proc: ProcInfo = Globals.catalog.procs[self.proc_id]
        self.record_type: str = self.read_record_type()
        self.log_type: str = self.read_log_type()
        self.flags: int = self.read_flags()
        self.strings_file_type_int = self.flags & firehose_trace_point_flags[FIREHOSE_TRACE_POINT_FLAG_STRING_FILE_TYPE]
        if self.strings_file_type_int not in firehose_trace_point_strings_file_types.keys():
            raise ValueError("Bad strings file type")
        self.strings_file_type = firehose_trace_point_strings_file_types[self.strings_file_type_int]
        self.flags_dict: dict = self.parse_flags()
        self.format_str_reference: int = self.read_format_string_reference()
        self.fmt_str_msb_on: bool = False
        if self.check_format_s():
            self.format_string = "%s"
        self.format_values: list = list()  # those come from either the private data or the value data
        self.data_sizes_and_offsets: dict = dict()  # this is filled via the read_data_items() method
        self.tid: int = self.read_tid()
        self.time_delta: int = self.read_time_delta()
        self.data_size: int = self.read_data_size()
        self.data_offset: int = self.fd.tell()
        self.read_data()
        if self.fd.tell() != self.data_offset + self.data_size:
            self.go_to_end_of_tracepoint()
        if not self.fmt_str_msb_on:
            self.format_string = self.read_format_string()
        self.align_cursor()

    def check_format_s(self):
        msb = self.format_str_reference & 0x80000000
        self.format_str_reference &= 0x7fffffff
        if msb:
            self.fmt_str_msb_on = True
        return msb

    def parse_flags(self):
        flags = dict()
        string_file_type = self.flags & firehose_trace_point_flags[FIREHOSE_TRACE_POINT_FLAG_STRING_FILE_TYPE]

        if string_file_type not in firehose_trace_point_strings_file_types.keys():
            raise ValueError("Invalid string file type")

        flags[FIREHOSE_TRACE_POINT_FLAG_STRING_FILE_TYPE] = firehose_trace_point_strings_file_types[string_file_type]

        flags[FIREHOSE_TRACE_POINT_FLAG_HAS_CURRENT_AID] = self.flags & firehose_trace_point_flags[
            FIREHOSE_TRACE_POINT_FLAG_HAS_CURRENT_AID] != 0
        flags[FIREHOSE_TRACE_POINT_FLAG_HAS_OTHER_AID] = self.flags & firehose_trace_point_flags[FIREHOSE_TRACE_POINT_FLAG_HAS_OTHER_AID] != 0
        flags[FIREHOSE_TRACE_POINT_FLAG_HAS_UNIQUE_PID] = self.flags & firehose_trace_point_flags[
            FIREHOSE_TRACE_POINT_FLAG_HAS_UNIQUE_PID] != 0
        flags[FIREHOSE_TRACE_POINT_FLAG_HAS_LARGE_OFFSET] = self.flags & firehose_trace_point_flags[
            FIREHOSE_TRACE_POINT_FLAG_HAS_LARGE_OFFSET] != 0
        flags[FIREHOSE_TRACE_POINT_FLAG_HAS_PRIVATE_DATA] = self.flags & firehose_trace_point_flags[
            FIREHOSE_TRACE_POINT_FLAG_HAS_PRIVATE_DATA] != 0
        flags[FIREHOSE_TRACE_POINT_FLAG_HAS_SUBSYSTEM] = self.flags & firehose_trace_point_flags[
            FIREHOSE_TRACE_POINT_FLAG_HAS_SUBSYSTEM] != 0
        flags[FIREHOSE_TRACE_POINT_FLAG_HAS_RULES] = self.flags & firehose_trace_point_flags[
            FIREHOSE_TRACE_POINT_FLAG_HAS_RULES] != 0
        flags[FIREHOSE_TRACE_POINT_FLAG_HAS_OVERSIZE] = self.flags & firehose_trace_point_flags[
            FIREHOSE_TRACE_POINT_FLAG_HAS_OVERSIZE] != 0
        flags[FIREHOSE_TRACE_POINT_FLAG_HAS_BACKTRACE] = self.flags & firehose_trace_point_flags[
            FIREHOSE_TRACE_POINT_FLAG_HAS_BACKTRACE] != 0
        flags[FIREHOSE_TRACE_POINT_FLAG_HAS_NAME_REF] = self.flags & firehose_trace_point_flags[
            FIREHOSE_TRACE_POINT_FLAG_HAS_NAME_REF] != 0

        return flags

    def read_record_type(self):
        r_type = struct.unpack("<B", self.fd.read(FIREHOSE_TRACE_POINT_RECORD_TYPE_SIZE))[0]
        # print(hex(r_type))
        if r_type not in firehose_trace_point_record_types.keys():
            raise ValueError("invalid record type")
        return firehose_trace_point_record_types[r_type]

    def read_log_type(self):
        l_type = struct.unpack("<B", self.fd.read(FIREHOSE_TRACE_POINT_LOG_TYPE_SIZE))[0]
        # print(hex(l_type))
        if l_type not in log_types.keys():
            raise ValueError("invalid record type")
        return log_types[l_type]

    def read_flags(self):
        return struct.unpack("<H", self.fd.read(FIREHOSE_TRACE_POINT_FLAGS_TYPE_SIZE))[0]

    def read_format_string_reference(self):
        return struct.unpack("<I", self.fd.read(FIREHOSE_TRACE_POINT_FORMAT_STRING_REFERENCE_SIZE))[0]

    def read_tid(self):
        return struct.unpack("<Q", self.fd.read(FIREHOSE_TRACE_POINT_TID_SIZE))[0]

    def read_time_delta(self):
        return utils.read_48_bits_little_endian(self.fd)

    def read_data_size(self):
        return struct.unpack("<H", self.fd.read(FIREHOSE_TRACE_POINT_DATA_SIZE))[0]

    def read_private_data(self):
        if (FIREHOSE_PRIVATE_VALUE_DATA_RANGE_TYPE not in self.data_sizes_and_offsets.keys() or
                self.firehose_main_chunk.private_data is None):
            return
        source_private_data = self.firehose_main_chunk.private_data
        for private_metadata in self.data_sizes_and_offsets[FIREHOSE_PRIVATE_VALUE_DATA_RANGE_TYPE]:
            offset = private_metadata["offset"]
            size = private_metadata["size"]
            self.trace_point_private_data.append(source_private_data[offset:size])

    def read_from_value_data_range(self, base_offset: int, value_type: str):
        for metadata in self.data_sizes_and_offsets[value_type]:
            self.fd.seek(base_offset + metadata["offset"])
            value = self.fd.read(metadata["size"])
            if value_type == FIREHOSE_STRING_VALUE_DATA_RANGE_TYPE:
                value = value[0:-len("\x00")].decode('utf-8')
            else:
                value = value.hex()
            self.format_values.append(value)

    def read_value_data(self):
        values_data_offset = self.fd.tell()
        if FIREHOSE_STRING_VALUE_DATA_RANGE_TYPE in self.data_sizes_and_offsets.keys():
            self.read_from_value_data_range(values_data_offset, FIREHOSE_STRING_VALUE_DATA_RANGE_TYPE)
        if FIREHOSE_BINARY_VALUE_DATA_RANGE_TYPE in self.data_sizes_and_offsets.keys():
            self.read_from_value_data_range(values_data_offset, FIREHOSE_BINARY_VALUE_DATA_RANGE_TYPE)

    def read_data_item(self):
        # The value type determine the type of the corresponding to the string format For example, for such string
        # format: "%p address is in procname: %s, proc_pid: %d address space" We'll have three items in the array.
        # For the %p format, the value type will be 0x00 (32/64 bit value) and the data size will be either 4 or 8
        # same for the %d format for the %s format, the value type will be either 0x20, 0x22, 0x40 - those define are
        # data items with value range data, this means that the data item contain offset relative to the value data
        # section and size of the string to be read from that offset

        def read_int_float_val(size, struct_string: str):
            data = struct.unpack(struct_string, self.fd.read(size))[0]
            self.format_values.append(hex(data))

        def read_value_data_range(type_of_val: str):
            value_offset = struct.unpack("<H", self.fd.read(FIREHOSE_TRACE_POINT_DATA_ITEM_VALUE_DATA_SIZE_SIZE))[0]
            value_size = struct.unpack("<H", self.fd.read(FIREHOSE_TRACE_POINT_DATA_ITEM_VALUE_DATA_OFFSET_SIZE))[0]
            if type_of_val not in self.data_sizes_and_offsets.keys():
                self.data_sizes_and_offsets[type_of_val] = list()
            self.data_sizes_and_offsets[type_of_val].append({"offset": value_offset, "size": value_size})

        def read_value_data_private_formatted_string():
            self.fd.read(4)
            self.format_values.append("<private>")

        value_type = struct.unpack("<B", self.fd.read(FIREHOSE_TRACE_POINT_DATA_ITEM_VALUE_TYPE_SIZE))[0]
        data_size = struct.unpack("<B", self.fd.read(FIREHOSE_TRACE_POINT_DATA_ITEM_DATA_SIZE))[0]
        if value_type in FIREHOSE_TRACE_POINT_VALUE_TYPE_STRING_RANGE:
            read_value_data_range(FIREHOSE_STRING_VALUE_DATA_RANGE_TYPE)
            return
        if value_type in FIREHOSE_TRACE_POINT_VALUE_TYPE_PRIVATE_RANGE:
            read_value_data_range(FIREHOSE_PRIVATE_VALUE_DATA_RANGE_TYPE)
            return
        if value_type in FIREHOSE_TRACE_POINT_VALUE_TYPE_BINARY_RANGE:
            read_value_data_range(FIREHOSE_BINARY_VALUE_DATA_RANGE_TYPE)
            return
        if value_type in FIREHOSE_TRACE_POINT_VALUE_TYPE_INT_OR_FLOAT:
            if data_size not in FIREHOSE_TRACE_POINT_STRUCT_STRINGS_BY_SIZE.keys():
                raise ValueError("Invalid data size !")
            read_int_float_val(data_size, FIREHOSE_TRACE_POINT_STRUCT_STRINGS_BY_SIZE[data_size])
            return
        if value_type in FIREHOSE_TRACE_POINT_VALUE_TYPE_32_BIT_PRIVATE:
            read_value_data_private_formatted_string()
            return
        self.fd.read(data_size)

    def read_data_items(self, num_of_items: int):
        for i in range(num_of_items):
            self.read_data_item()

    @abstractmethod
    def read_format_string(self):
        pass

    @abstractmethod
    def read_data(self):
        pass

    def go_to_end_of_tracepoint(self):
        self.fd.seek(self.data_offset + self.data_size)

    def print_v3(self):
        print(f"""
        record type: {self.record_type}
        log type: {self.log_type}
        flags: {self.flags_dict}
        format string reference size: {self.format_str_reference}
        thread id: {self.tid}
        time delta: {self.time_delta}
        data size: {self.data_size}
        private data: {self.trace_point_private_data}""")


class ActivityTracePoint(FirehoseTracePoint):

    def __init__(self, fd: io.BufferedReader, firehose_chunk: FirehoseChunk):
        self.aid: str = "N/A"
        self.pid: int = 0
        self.other_aid: str = "N/A"
        self.new_aid: str = "N/A"
        self.load_addr_lower: int = 0
        self.large_offset_data: int = 0
        self.uuid_entry_load_addr_upper: int = 0
        self.uuid_text_id: str = "N/A"
        self.large_shared_cache_data: int = 0
        super().__init__(fd, firehose_chunk)

    def read_aid(self):
        if self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_CURRENT_AID]:
            return hex(struct.unpack("<Q", self.fd.read(8))[0])

    def read_pid(self):
        if self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_UNIQUE_PID]:
            return struct.unpack("<Q", self.fd.read(8))[0]

    def read_other_aid(self):
        if self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_OTHER_AID]:
            return hex(struct.unpack("<Q", self.fd.read(8))[0])

    def read_new_aid(self):
        if self.log_type != LOG_TYPE_USER_ACTION:
            return hex(struct.unpack("<Q", self.fd.read(8))[0])

    def read_uuid_entry_load_address_lower(self):
        return struct.unpack("<I", self.fd.read(4))[0]

    def read_large_offset_data(self):
        if self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_LARGE_OFFSET]:
            return struct.unpack("<H", self.fd.read(2))[0]

    def read_uuid_entry_load_address_upper(self):
        if self.strings_file_type == ABSOLUTE_FILE_TYPE:
            return struct.unpack("<H", self.fd.read(2))[0]

    def read_uuidtext_id(self):
        if self.strings_file_type == UUID_RELATIVE_FILE_TYPE:
            return uuid.UUID(self.fd.read(16).hex()).hex

    def read_large_shared_cache_data(self):
        if self.strings_file_type == LARGE_SHARED_CACHE_FILE_TYPE:
            return struct.unpack("<H", self.fd.read(2))[0]

    def read_format_string(self):
        pass

    def read_data(self):
        self.aid = self.read_aid()
        self.pid = self.read_pid()
        self.other_aid = self.read_other_aid()
        self.new_aid = self.read_new_aid()
        self.load_addr_lower = self.read_uuid_entry_load_address_lower()
        self.large_offset_data = self.read_large_offset_data()
        self.uuid_entry_load_addr_upper = self.read_uuid_entry_load_address_upper()
        self.uuid_text_id = self.read_uuidtext_id()
        self.large_offset_data = self.read_large_shared_cache_data()


class LossTracePoint(FirehoseTracePoint):
    def __init__(self, fd: io.BufferedReader, firehose_chunk: FirehoseChunk):
        self.start_time: int = 0
        self.end_time: int = 0
        self.num_of_msgs: int = 0
        super().__init__(fd, firehose_chunk)

    def read_data(self):
        self.start_time = struct.unpack(">Q", self.fd.read(8))[0]
        self.end_time = struct.unpack(">Q", self.fd.read(8))[0]
        self.num_of_msgs = struct.unpack(">Q", self.fd.read(8))[0]

    def read_format_string(self):
        pass


class TraceTracePoint(FirehoseTracePoint):

    def __init__(self, fd: io.BufferedReader, firehose_chunk: FirehoseChunk):
        self.uuid_entry_load_address_lower: int = 0
        self.num_of_values: int = 0
        super().__init__(fd, firehose_chunk)

    def read_uuid_entry_load_address_lower(self):
        self.uuid_entry_load_address_lower = struct.unpack("<I", self.fd.read(4))

    def read_format_string(self):
        pass

    def read_data(self):
        return self.fd.read(self.data_size)


class LogTracePoint(FirehoseTracePoint):
    def __init__(self, fd: io.BufferedReader, firehose_chunk: FirehoseChunk):
        # Has current activity identifier flag (0x0001) is set
        self.current_activity_id: int = 0
        # Has private data range flag (0x0100) is set
        self.private_data_range_off: int = 0
        # common
        self.uuid_entry_load_addr_lower: int = 0
        # If strings file type == 0x0008
        self.uuid_entry_load_addr_upper: int = 0
        # Has large offset flag (0x0020) is set
        self.large_offset_data: int = 0
        # If strings file type == 0x000a
        self.uuid_text_file_identifier: str = "N/A"
        # If strings file type == 0x000c
        self.large_shared_cache_data: int = 0
        # Has sub system flag (0x0200) is set
        self.subsystem: str = "N/A"
        self.category: str = "N/A"
        # Has rules flag (0x0400) is set
        self.ttl: int = 0
        # Has oversize data reference flag (0x0800) is set
        self.oversize_data_reference: int = 0
        self.num_of_data_items: int = 0
        self.data_items: list = list()
        # if backtrace flag (0x1000) is set 0 values data also contain backtraces
        self.backtrace: dict = dict()
        super().__init__(fd, firehose_chunk)

    def read_current_aid(self):
        if self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_CURRENT_AID]:
            self.current_activity_id = struct.unpack("<Q", self.fd.read(FIREHOSE_TRACE_POINT_LOG_ACTIVITY_ID_SIZE))[0]
            # print(f"current activity id: {self.current_activity_id}")

    def read_private_data_range(self):
        if self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_PRIVATE_DATA]:
            self.private_data_range_off = \
                struct.unpack("<I", self.fd.read(FIREHOSE_TRACE_POINT_LOG_PRIVATE_DATA_RANGE_SIZE))[0]
        # print(f"private data range: {self.private_data_range_off}")

    def read_current_uuid_entry_load_addr_lower(self):
        load_addr_lower = self.fd.read(FIREHOSE_TRACE_POINT_LOG_UUID_ENTRY_LOAD_ADDRESS_LOWER_SIZE)
        # print(load_addr_lower.hex())
        self.uuid_entry_load_addr_lower = struct.unpack("<I", load_addr_lower)[0]
        # print(f"uuid entry load addr lower: {self.uuid_entry_load_addr_lower}")

    def read_large_offset_data(self):
        if self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_LARGE_OFFSET]:
            large_offset = struct.unpack("<H", self.fd.read(FIREHOSE_TRACE_POINT_LOG_LARGE_OFFSET_DATA_SIZE))[0]
            self.large_offset_data = large_offset << 31 | self.format_str_reference
            # print(f"large offset data: {self.large_offset_data}")

    def read_current_uuid_entry_load_addr_upper(self):
        if self.strings_file_type == ABSOLUTE_FILE_TYPE:
            self.uuid_entry_load_addr_upper = \
                struct.unpack("<H", self.fd.read(FIREHOSE_TRACE_POINT_LOG_UUID_ENTRY_LOAD_ADDRESS_UPPER_SIZE))[0]
            # print(f"uuid entry load addr upper: {self.uuid_entry_load_addr_upper}")

    def read_uuidtext_file_id(self):
        if self.strings_file_type == UUID_RELATIVE_FILE_TYPE:
            self.uuid_text_file_identifier = uuid.UUID(self.fd.read(FIREHOSE_TRACE_POINT_LOG_UUID_SIZE).hex())
            # print(f"uuid text file identifier: {self.uuid_text_file_identifier}")

    def read_large_shared_cache_data(self):
        if self.strings_file_type == LARGE_SHARED_CACHE_FILE_TYPE:
            shared_cache_data = \
                struct.unpack("<H", self.fd.read(FIREHOSE_TRACE_POINT_LOG_LARGE_SHARED_CACHE_DATA_SIZE))[0]
            self.large_shared_cache_data = shared_cache_data << 31 | self.format_str_reference
            # print(f"large shared cache data: {self.large_shared_cache_data}")

    def read_subsystem(self):
        if self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_SUBSYSTEM]:
            subsystem_id = struct.unpack("<H", self.fd.read(FIREHOSE_TRACE_POINT_LOG_SUBSYSTEM_ID_SIZE))[0]
            if subsystem_id not in self.proc.proc_subsystems.keys():
                raise ValueError("Invalid subsystem id")
            self.subsystem = self.proc.proc_subsystems[subsystem_id]["subsystem"]
            self.category = self.proc.proc_subsystems[subsystem_id]["category"]
            # print(f"subsystem: {self.subsystem}")

    def read_ttl(self):
        if self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_RULES]:
            self.current_activity_id = struct.unpack("<B", self.fd.read(FIREHOSE_TRACE_POINT_LOG_TTL_SIZE))[0]
            # print(f"ttl: {self.ttl}")

    def read_format_string(self):
        if self.strings_file_type == SHARED_CACHE_FILE_TYPE:
            if self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_LARGE_OFFSET]:
                dsc_str_info = DSC(self.proc.dsc_uuid).parse().read_string_reference(self.large_offset_data)
            else:
                dsc_str_info = DSC(self.proc.dsc_uuid).parse().read_string_reference(self.format_str_reference)
            self.sender_uuid = dsc_str_info[1]
            self.sender_image_path = dsc_str_info[2]
            return dsc_str_info[0]
        if self.strings_file_type == UUID_RELATIVE_FILE_TYPE:
            uuid_text_info = UuidText(self.uuid_text_file_identifier).parse()
            self.sender_image_path = uuid_text_info.footer
            return uuid_text_info.read_string_reference(self.format_str_reference)
        if self.strings_file_type == MAIN_EXE_FILE_TYPE:
            uuid_text_info = UuidText(self.proc.main_uuid).parse()
            self.sender_image_path = uuid_text_info.footer
            return uuid_text_info.read_string_reference(self.format_str_reference)
        if self.strings_file_type == ABSOLUTE_FILE_TYPE:
            pass

    def read_oversize_data_reference(self):
        if self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_OVERSIZE]:
            self.oversize_data_reference = \
                struct.unpack("<H", self.fd.read(FIREHOSE_TRACE_POINT_LOG_OVERSIZE_DATA_REFERENCE_SIZE))[0]
            # print(f"oversize data reference: {self.oversize_data_reference}")

    def read_unknown(self):
        self.fd.read(FIREHOSE_TRACE_POINT_LOG_UNKNOWN_SIZE)

    def read_num_of_data_items(self):
        self.num_of_data_items = struct.unpack("<B", self.fd.read(FIREHOSE_TRACE_POINT_LOG_NUM_OF_DATA_ITEMS_SIZE))[0]
        # print(f"number of data items: {self.num_of_data_items}")

    def read_backtrace(self):
        if not self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_BACKTRACE]:
            return
        self.fd.read(FIREHOSE_TRACE_POINT_LOG_BACKTRACE_UNKNOWN_1ST_SIZE)
        self.fd.read(FIREHOSE_TRACE_POINT_LOG_BACKTRACE_UNKNOWN_2ND_SIZE)
        num_of_images = struct.unpack("<B", self.fd.read(FIREHOSE_TRACE_POINT_LOG_BACKTRACE_NUMBER_OF_IMAGES_SIZE))[0]
        num_of_frames = struct.unpack("<B", self.fd.read(FIREHOSE_TRACE_POINT_LOG_BACKTRACE_NUMBER_OF_FRAMES_SIZE))[0]
        uuids = list()
        for i in range(num_of_images):
            current_uuid = uuid.UUID(self.fd.read(FIREHOSE_TRACE_POINT_LOG_UUID_SIZE).hex())
            uuids.append(current_uuid)
        offsets = list()
        for i in range(num_of_frames):
            current_offset = struct.unpack("<H", self.fd.read(2))
            offsets.append(current_offset)
        indices = list()
        for i in range(num_of_frames):
            current_index = struct.unpack("<B", self.fd.read(1))
            indices.append(current_index)
        self.backtrace["offsets"] = offsets
        self.backtrace["indices"] = indices

    def read_data(self):
        self.read_current_aid()
        self.read_private_data_range()
        self.read_current_uuid_entry_load_addr_lower()
        self.read_large_offset_data()
        self.read_current_uuid_entry_load_addr_upper()
        self.read_uuidtext_file_id()
        self.read_large_shared_cache_data()
        self.read_subsystem()
        self.read_ttl()
        self.read_oversize_data_reference()
        self.read_unknown()
        self.read_num_of_data_items()
        self.read_data_items(self.num_of_data_items)
        self.read_backtrace()
        self.read_value_data()
        self.read_private_data()

    def print_v3(self):
        super().print_v3()
        print(f"""
            record type: {self.record_type}
            log type: {self.log_type}
            aid: {self.current_activity_id}
            private data range: {self.private_data_range_off}
            uuid entry load address lower: {self.uuid_entry_load_addr_lower}
            large data offset: {self.large_offset_data}
            uuid entry load address upper: {self.uuid_entry_load_addr_upper}
            uuidtext file id: {self.uuid_text_file_identifier}
            large shared cache data: {self.large_shared_cache_data}
            subsystem: {self.subsystem}.{self.category}
            ttl: {self.ttl}
            oversize data reference: {self.oversize_data_reference}
            string format values: {self.format_values} 
            string format: {self.format_string}
            sender image path: {self.sender_image_path}
            sender image uuid: {self.sender_uuid}
            proc path: {self.proc.path}
        """)


class SignpostTracePoint(LogTracePoint):
    def __init__(self, fd: io.BufferedReader, firehose_chunk: FirehoseChunk):
        self.name_string_reference_lower: int = 0
        self.name_string_reference_upper: int = 0
        self.name_string_reference: int = 0
        self.signpost_id: str = "N/A"
        super().__init__(fd, firehose_chunk)

    def read_name_string_ref(self):
        if self.flags_dict[FIREHOSE_TRACE_POINT_FLAG_HAS_NAME_REF]:
            self.name_string_reference_lower = struct.unpack(">I", self.fd.read(4))[0]
            if self.flags[FIREHOSE_TRACE_POINT_FLAG_HAS_LARGE_OFFSET]:
                self.name_string_reference_upper = struct.unpack(">I", self.fd.read(4))[0]
                self.name_string_reference = (self.name_string_reference_lower & 0x7fffffff |
                                              self.name_string_reference_upper << 31)

    def read_signpost_id(self):
        self.signpost_id = self.fd.read(8).hex()

    def read_data(self):
        self.read_current_aid()
        self.read_private_data_range()
        self.read_current_uuid_entry_load_addr_lower()
        self.read_large_offset_data()
        self.read_current_uuid_entry_load_addr_upper()
        self.read_uuidtext_file_id()
        self.read_large_shared_cache_data()
        self.read_subsystem()
        self.read_signpost_id()
        self.read_ttl()
        self.read_oversize_data_reference()
        self.read_name_string_ref()
        self.read_unknown()
        self.read_num_of_data_items()
        self.read_data_items(self.num_of_data_items)
        self.read_value_data()
        self.read_private_data()


class UnusedTracePoint(FirehoseTracePoint):
    def __init__(self, fd: io.BufferedReader, firehose_chunk: FirehoseChunk):
        super().__init__(fd, firehose_chunk)

    def read_data(self):
        return self.fd.read(self.data_size)


trace_point_log_type_ctors = {0x00: UnusedTracePoint, 0x02: ActivityTracePoint, 0x03: TraceTracePoint,
                              0x04: LogTracePoint, 0x06: SignpostTracePoint, 0x07: LossTracePoint}
