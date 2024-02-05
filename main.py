from TraceParserV3 import *
import sys
import base_file
# TODO: create a dictionary for each member of the structure containing the size of each member and the struct size
#  and endianity string

# TODO: figure out a way to make a generic parser mechanism.
#  Maybe by parsing a plist representing the structure, offset, sizes, etc.


def usage():
    print("""[~] usage: python3 main.py <path to TraceV3 file> <path to uuidtext directory>""")


def print_not_exists(path: str):
    print(f"{path} does not exists")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        usage()

    traceV3_file = sys.argv[1]
    uuid_text_path = sys.argv[2]
    if not Path(traceV3_file).exists():
        print_not_exists(traceV3_file)
    if not Path(uuid_text_path).exists():
        print_not_exists(uuid_text_path)

    base_file.BASE_DIR = Path(uuid_text_path)
    trace_parser = TraceV3Parser(traceV3_file)
    trace_parser.parse_v3_chunks()

    # a = UuidText(Path("/private/var/db/uuidtext/1B/1980EEE15A310883D2C85FD0249F86")).parse()
    # a.read_string_reference()
    # b = DSC(Path("/private/var/db/uuidtext/dsc/C4E0C302D68B3B569F5A6C3FBE5367CB")).parse()
    # b.read_string_reference()