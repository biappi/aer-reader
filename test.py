#!/usr/bin/env python

import sys, gzip, re, struct, collections, pprint, itertools
from os import path


def read_aer_file(filename):
    "returns: (aer_header, content)"

    with open(filename, "r") as aer_f:
        header  = aer_f.readline()

        # NOTE(willy): those two lines of code seem not to be needed, as
        #              gzip.GzipFile does not seem to rewind the file.
        #content = aer_f.read()
        #gzipped = StringIO.StringIO(content)

        with gzip.GzipFile(fileobj=aer_f) as dat_f:
            return (header, dat_f.read())


def is_print(c):
    return ((0x20 <= ord(c)) and (ord(c) < 0x7f))


def hexify(buf):
    for line_nr in xrange(0, (len(buf) / 0x10) + 1):
        offset   = line_nr * 0x10
        content  = buf[offset : offset + 0x10]
        remain   = 0x10 - len(content)
        
        elements = (("%02x" % ord(i)) for i in content)
        spaces   = ("  " for _ in xrange(0, remain))
        hexline  = " ".join (itertools.chain(elements, spaces))

        chars    = (i if is_print(i) else '.'
                        for i in content)
        ascline  = "".join(chars)

        print "%08x  %s  %s" % (offset, hexline, ascline)


def chunk_by(l, by):
    return [l[i * by : (i * by) + by]
        for i in xrange(len(l) / by)]

class UNK(str):
    "tag a string to be an unknown value"
    
    def __repr__(self):
        if len(self) == 0: return "''"
        string = str(self if self[-1] != '\0' else self[:-1])
        return repr(string)

class URL(str):
    "tag a string to be an url"
    pass

def tag_unknown_to_value(value):
    return UNK(value)

def tag_string_to_value(value):
    return value if value[-1] != '\0' else value[:-1]

def tag_int_to_value(value):
    return struct.unpack('<i', value)[0]

def tag_bool_to_value(value):
    return bool(tag_int_to_value(value))

def tag_double_to_value(value):
    if len(value) == 4:
        return struct.unpack('<i', value)[0]
    else:
        return struct.unpack('<d', value)[0]

def tag_url_to_value(value):
    return URL(tag_string_to_value(value))

def tag_ints_to_value(value):
    return tuple(tag_int_to_value(i)
        for i in chunk_by(value, 4))

def tag_doubles_to_value(value):
    return tuple(tag_double_to_value(i)
        for i in chunk_by(value, 8))

def tag_types_to_value(value):
    return tuple(chunk_by(value, 4))


tag_to_value_functions = {
    'aplt': tag_bool_to_value,
    'cnpr': tag_bool_to_value,
    'ilbo': tag_bool_to_value,
    'isab': tag_bool_to_value,
    'isbo': tag_bool_to_value,
    'lite': tag_bool_to_value,
    'loop': tag_bool_to_value,
    'rlbo': tag_bool_to_value,
    'rldl': tag_bool_to_value,
    'rlll': tag_bool_to_value,
    'rlsu': tag_bool_to_value,
    'rsbo': tag_bool_to_value,
    'scty': tag_bool_to_value,
    'strt': tag_bool_to_value,
    'subt': tag_bool_to_value,

    'aple': tag_int_to_value,
    'avcl': tag_int_to_value,
    'dpth': tag_int_to_value,
    'face': tag_int_to_value,
    'facs': tag_int_to_value,
    'ivis': tag_int_to_value,
    'lock': tag_int_to_value,
    'nwst': tag_int_to_value,
    'texr': tag_int_to_value,

    'bl..': tag_double_to_value,
    'btwi': tag_double_to_value,
    'ca..': tag_double_to_value,
    'da..': tag_double_to_value,
    'db..': tag_double_to_value,
    'de..': tag_double_to_value,
    'dsbr': tag_double_to_value,
    'embr': tag_double_to_value,
    'gr..': tag_double_to_value,
    'hite': tag_double_to_value,
    'lmss': tag_double_to_value,
    'mm..': tag_double_to_value,
    'mn..': tag_double_to_value,
    'offu': tag_double_to_value,
    'offv': tag_double_to_value,
    'plny': tag_double_to_value,
    'rd..': tag_double_to_value,
    'rota': tag_double_to_value,
    'sb..': tag_double_to_value,
    'sfbr': tag_double_to_value,
    'sgrn': tag_double_to_value,
    'sizu': tag_double_to_value,
    'sizv': tag_double_to_value,
    'sblu': tag_double_to_value,
    'so..': tag_double_to_value,
    'sred': tag_double_to_value,
    'su..': tag_double_to_value,
    'sv..': tag_double_to_value,
    'thik': tag_double_to_value,
    'tpwi': tag_double_to_value,
    'widt': tag_double_to_value,
    'wrpv': tag_double_to_value,
    'wrpu': tag_double_to_value,

    'icon': tag_url_to_value,
    'irur': tag_url_to_value,
    'jvsr': tag_url_to_value,
    'urln': tag_url_to_value,
    'wrul': tag_url_to_value,

    'cn3s': tag_ints_to_value,
    'list': tag_ints_to_value,
    'lmls': tag_ints_to_value,
    'stl2': tag_ints_to_value,

    'lkdr': tag_doubles_to_value,
    'oRNt': tag_doubles_to_value,
    'oRnt': tag_doubles_to_value,
    'size': tag_doubles_to_value,
    'vals': tag_doubles_to_value,

    'idnt': tag_types_to_value,
    'stid': tag_types_to_value,
}


def tag_content_to_value(tag_and_content):
    tag, content = tag_and_content
    tag_to_value = tag_to_value_functions.get(tag, tag_unknown_to_value)
    return tag, tag_to_value(content)


TagLenStruct = struct.Struct("<4sH")
def parse_tag_len_value(buf, offset):

    tag, length = TagLenStruct.unpack_from(buf, offset)

    # NOTE(willy): if length is 0xffff, the value of the current tag
    #              is the entirety of the remainer of the chunk's
    #              data.

    if length != 0xffff:
        next_offset = offset + TagLenStruct.size + length
        value = buf[offset + TagLenStruct.size : next_offset]
    else:
        next_offset = len(buf) + 1
        value = buf[offset + TagLenStruct.size:]

    return (next_offset, (tag, value))


def iterate_tag_values(buf):
    offset = 0
    while offset < len(buf):
        offset, tlv = parse_tag_len_value(buf, offset)
        yield tlv

class ChunkHeaderNotRecognized(Exception): pass


class Chunk(collections.namedtuple('Chunk',
        ('idx', 'head1', 'head2', 'data')
    )):

    @staticmethod
    def iterate_from_data(data):
        for num, line in enumerate(re.split(r"\n(?=[A-Z0-9]{4}\d)", data)):
            head = re.match(r"^([A-Z0-9]{4})(\d+):", line)

            if not head:
                raise ChunkHeaderNotRecognized

            yield Chunk(
                num,
                head.group(1),
                head.group(2),
                line[len(head.group(1) + head.group(2)) + 1:].strip(),
            )

    def parse(self):
        urls = set()
        data = {}

        for item in iterate_tag_values(self.data):
            tagged_item = tag_content_to_value(item)
            data[tagged_item[0]] = tagged_item[1]

            if isinstance(tagged_item[1], URL):
                urls.add(tagged_item[1])

        return data, urls

    def dump(self, parsed_data=None):
        data = parsed_data or repr(self.data[:70])
        print str(self.idx).zfill(4), self.head1, self.head2.zfill(3), data


def world_name_from_filename(filename):
    return path.splitext(path.basename(filename))[0]


def convert_aer_to_dat(filename):
    _, content   = read_aer_file(filename)
    dat_filename = world_name_from_filename(filename) + ".dat"

    with open(dat_filename + ".dat", "wb") as dst_f:
        dst_f.write(content)


def default_urls(aer_filename):
    return set((
        "./Viewer.png",
        "./%s.ctl" % (world_name_from_filename(aer_filename),)
    ))


def main(aer_name, parse=False, save_dat_file=False):
    header, dat = read_aer_file (aer_name)
    urls        = default_urls  (aer_name)

    for chunk in Chunk.iterate_from_data(dat):
        if parse:
            parsed_data, parsed_urls = chunk.parse()
            urls.update(parsed_urls)
        else:
            parsed_data = None

        chunk.dump(parsed_data)

    print "----"
    for url in sorted(urls):
        print url

if __name__ == "__main__":
    try: aer_name = sys.argv[1]
    except: print "usage: %s AER_FILE_NAME <parse>"; sys.exit()

    main(
        aer_name,
        parse=len(sys.argv) > 2 and sys.argv[2],
        save_dat_file=False
    )
