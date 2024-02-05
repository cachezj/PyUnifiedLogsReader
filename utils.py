import io
import struct
from consts import *
import lz4.block
from lz4 import *
from typing import Union
import hexdump


def decompress_lz4_buffer(compressed_buffer, uncompressed_size: int):
    vv = b''
    vv = lz4.block.decompress(compressed_buffer, uncompressed_size=uncompressed_size, return_bytearray=vv)
    return vv


def decompress_lz4_file(file_path):
    with open(file_path, "rb") as file:
        compressed_buffer = file.read()
    return decompress_lz4_buffer(compressed_buffer)


def read_string_from_buf(buf: str, offset: int):
    current_letter = buf[offset]
    string = ""
    while current_letter != str('\x00'):
        offset += 1
        string += current_letter
        current_letter = buf[offset]
    return string


def strings_list_to_null_terminated_strings_buffer(strings_list: list):
    return chr(0).join(strings_list) + chr(0)


def read_and_return_to_cursor(fd: io.BufferedReader, offset, size):
    old = fd.tell()
    fd.seek(offset)
    if size:
        data = fd.read(size)
    else:
        current_ascii = struct.unpack("<B", fd.read(1))[0]
        string = ""
        while current_ascii != 0:
            string += chr(current_ascii)
            current_ascii = struct.unpack("<B", fd.read(1))[0]
        data = string
    fd.seek(old)
    return data


def read_null_terminated_string_from_fd(fd: io.BufferedReader, size):
    return fd.read(size).decode('utf-8').replace('\x00', '')


def read_proc_id(fd: io.BufferedReader):
    proc_id1 = struct.unpack("<Q", fd.read(CATALOG_CHUNK_PROC_ENTRY_PROC_ID_1ST_SIZE))[0]
    proc_id2 = struct.unpack("<I", fd.read(CATALOG_CHUNK_PROC_ENTRY_PROC_ID_2ND_SIZE))[0]
    return f"{proc_id1}@{proc_id2}"


def read_48_bits_little_endian(from_: io.BufferedReader):
    lower = struct.unpack("<I", from_.read(4))[0]
    upper = struct.unpack("<H", from_.read(2))[0]
    return upper << 32 | lower
