import os

from TraceParserV3 import *
import sys
from accessories import base_file


# TODO: create a dictionary for each member of the structure containing the size of each member and the struct size
#  and endianity string

# TODO: figure out a way to make a generic parser mechanism.
#  Maybe by parsing a plist representing the structure, offset, sizes, etc.


def usage():
    print("""[~] usage: python3 main.py <path to TraceV3 file> <path to uuidtext directory>""")


def print_not_exists(path: str):
    print(f"{path} does not exists")


def run_tracev(traceV3_file, uuid_text):
    if not traceV3_file.exists():
        print_not_exists(traceV3_file)
        exit(1)
    if not uuid_text.exists():
        print_not_exists(uuid_text)
        exit(1)

    base_file.BASE_DIR = Path(uuid_text)
    trace_parser = TraceV3Parser(traceV3_file)
    trace_parser.parse_v3_chunks()


if __name__ == '__main__':
    if len(sys.argv) == 2:
        pp = sys.argv[1]
        project_path = Path(pp)

        for file in project_path.iterdir():
            if file.is_dir():
                for tracev in file.iterdir():
                    if 'tracev3' in tracev.suffix:
                        run_tracev(tracev, project_path)
            if 'tracev3' in file.suffix:
                run_tracev(file, project_path)
    else:
        traceV3_file_path = Path(sys.argv[1])
        uuid_text_path = Path(sys.argv[2])
        run_tracev(traceV3_file_path, uuid_text_path)
    if len(sys.argv) < 3:
        usage()
        exit(1)

    # a = UuidText(Path("/private/var/db/uuidtext/1B/1980EEE15A310883D2C85FD0249F86")).parse()
    # a.read_string_reference()
    # b = DSC(Path("/private/var/db/uuidtext/dsc/C4E0C302D68B3B569F5A6C3FBE5367CB")).parse()
    # b.read_string_reference()
