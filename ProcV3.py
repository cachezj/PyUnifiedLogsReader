from BaseV3 import *
from accessories.uuid_text import UuidText
import uuid

class ProcInfo(GenericTraceV3ChunkSection):
    def __init__(self, tracev3_fd: io.BufferedReader, uuids_offset: int, uuid_num: int, subsystems_offset: int):
        super().__init__(tracev3_fd)
        self.proc_info_offset_global: int = self.fd.tell()
        self.uuid_arr_offset: int = uuids_offset
        self.uuid_arr_length: int = uuid_num
        self.subsystems_offset: int = subsystems_offset
        self.entry_id: int = self.read_entry_id()
        self.flags: int = self.read_flags()
        self.main_uuid: str = self.read_main_uuid()
        self.dsc_uuid: str = self.read_dsc_uuid()
        self.proc_id: str = self.read_proc_id()
        self.pid: int = self.read_proc_pid()
        self.euid: int = self.read_proc_euid()
        self.path: str = self.read_path()
        self.read_unknown_1st()
        self.number_of_uuids: int = self.read_number_of_uuids()
        self.read_unknown_2nd()
        self.uuids_info: dict = self.read_uuids_info()
        self.number_of_subsystems: int = self.read_number_of_subsystems()
        self.read_unknown_3rd()
        self.proc_subsystems: dict = self.read_subsystems_info()
        self.align_cursor()

    def read_path(self):
        uuid_text_info = UuidText(self.main_uuid).parse()
        return uuid_text_info.footer

    def read_entry_id(self):
        return struct.unpack("<H", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_INDEX_SIZE))[0]

    def read_flags(self):
        return struct.unpack("<H", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_FLAGS_MEMBER_SIZE))[0]

    def read_unknown_1st(self):
        # We do nothing with it
        return self.fd.read(CATALOG_CHUNK_PROC_ENTRY_1ST_UNKNOWN_MEMBER_SIZE)

    def read_unknown_2nd(self):
        # We do nothing with it
        return self.fd.read(CATALOG_CHUNK_PROC_ENTRY_2ND_UNKNOWN_MEMBER_SIZE)

    def read_unknown_3rd(self):
        # We do nothing with it
        return self.fd.read(CATALOG_CHUNK_PROC_ENTRY_3RD_UNKNOWN_MEMBER_SIZE)

    def read_proc_id(self):
        return read_proc_id(self.fd)

    def read_proc_pid(self):
        return struct.unpack("<I", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_PROC_PID_SIZE))[0]

    def read_main_uuid(self):
        uuid_index = struct.unpack("<H", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_PROC_UUID_INDEX_SIZE))[0]
        if uuid_index < 0 or uuid_index > self.uuid_arr_length:
            raise ValueError("invalid uuid index")
        uuid_ = read_and_return_to_cursor(self.fd, self.uuid_arr_offset + uuid_index * CATALOG_CHUNK_UUID_SIZE,
                                          CATALOG_CHUNK_UUID_SIZE)
        return uuid.UUID(uuid_.hex()).hex

    def read_dsc_uuid(self):
        uuid_index = struct.unpack("<h", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_DSC_UUID_INDEX_SIZE))[0]

        if uuid_index > self.uuid_arr_length:
            raise ValueError("invalid dsc uuid index")

        if -1 == uuid_index:
            return "N/A"
        uuid_ = read_and_return_to_cursor(self.fd, self.uuid_arr_offset + uuid_index * CATALOG_CHUNK_UUID_SIZE, CATALOG_CHUNK_UUID_SIZE)
        return uuid.UUID(uuid_.hex()).hex

    def read_proc_euid(self):
        return struct.unpack("<I", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_PROC_EUID_SIZE))[0]

    def read_number_of_subsystems(self):
        return struct.unpack("<I", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_NUMBER_OF_SUBSYSTEMS_SIZE))[0]

    def read_subsystems_info(self):
        subsystems = dict()
        for i in range(self.number_of_subsystems):
            entry_id = struct.unpack("<H", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_SUBSYSTEM_ID_SIZE))[0]
            subsystem_off = \
            struct.unpack("<H", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_SUBSYSTEM_OFFSET_SIZE))[0]
            category_off = \
            struct.unpack("<H", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_CATEGORY_OFFSET_SIZE))[0]
            if self.subsystems_offset + subsystem_off > self.proc_info_offset_global:
                raise ValueError("invalid subsystem offset !")
            if self.subsystems_offset + category_off > self.proc_info_offset_global:
                raise ValueError("invalid catalog offset !")
            current_subsystem = read_and_return_to_cursor(self.fd, self.subsystems_offset + subsystem_off, 0)
            current_category = read_and_return_to_cursor(self.fd, self.subsystems_offset + category_off, 0)
            subsystems[entry_id] = {"subsystem": current_subsystem, "category": current_category}
        return subsystems

    def read_number_of_uuids(self):
        return struct.unpack("<I", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_UUID_NUM_SIZE))[0]

    def read_uuids_info(self):
        uuids = dict()
        for i in range(self.number_of_uuids):
            size = struct.unpack("<I", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_UUID_INFO_SIZE_SIZE))[0]
            self.fd.read(CATALOG_CHUNK_PROC_ENTRY_UUID_INFO_UNKNOWN_MEMBER_SIZE)
            index = struct.unpack("<H", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_UUID_INFO_INDEX_SIZE))[0]
            if index < 0 or index > self.uuid_arr_length:
                raise ValueError("invalid uuid index found in proc info !")
            load_addr_lower = \
            struct.unpack("<I", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_UUID_INFO_LOAD_ADDR_LOWER_SIZE))[0]
            load_addr_upper = \
            struct.unpack("<H", self.fd.read(CATALOG_CHUNK_PROC_ENTRY_UUID_INFO_LOAD_ADDR_UPPER_SIZE))[0]
            uuid_str = read_and_return_to_cursor(self.fd, self.uuid_arr_offset + index * CATALOG_CHUNK_UUID_SIZE, CATALOG_CHUNK_UUID_SIZE)
            uuids[uuid_str] = {"size": size, "load_addr_lower": load_addr_lower, "load_addr_upper": load_addr_upper}
        return uuids

    def print_v3(self):
        print(f"""
        proc_id: {self.proc_id}
        proc_uuid: {self.main_uuid}
        dsc_uuid: {self.dsc_uuid}
        pid: {self.pid}
        euid: {self.euid}
        subsystems: {self.proc_subsystems}
        uuids: {self.uuids_info}
        """)

    def json(self):
        return dict(
            processID=self.pid,
            effectiveUID=self.euid,
            processImageUUID=self.main_uuid,
            processImagePath=self.path

        )
