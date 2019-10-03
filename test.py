#!/usr/bin/env python

import sys, gzip, re, struct
from os import path

# Arrays: key + array size (little-endian?) + NULL + contents
# Strings: key + string length??? + NULL + contents + NULL

URLS = set()

def scan_line(num, buf):
    bool_keys = ["aplt", "cnpr", "ilbo", "isab", "isbo", "lite", "loop", "rlbo",
                 "rldl", "rlll", "rlsu", "rsbo", "scty", "strt", "subt"]
    int_keys = ["aple", "avcl", "dpth", "face", "facs", "ivis", "lock", "nwst",
                "texr"]
    dbl_keys = ["bl..", "btwi", "ca..", "da..", "db..", "de..", "dsbr", "embr",
                "gr..", "hite", "lmss", "mm..", "mn..", "offu", "offv", "plny",
                "rd..", "rota", "sb..", "sfbr", "sgrn", "sizu", "sizv", "sblu",
                "so..", "sred", "su..", "sv..", "thik", "tpwi", "widt", "wrpv",
                "wrpu"]
    url_keys = ["icon", "irur", "jvsr", "urln", "wrul"]
    ints_keys = ["cn3s", "list", "lmls", "stl2"]
    dbls_keys = ["lkdr", "oRNt", "oRnt", "size", "vals"]
    types_keys = ["idnt", "stid"]
    
    #print head.group(1)
    data = {}
    while buf:
        # Unpack a key.
        try:
            key = struct.unpack_from("<4s", buf)[0]
        except struct.error as err:
            print ">>> Warning: Object %i truncated." % num
            break
        buf = buf[struct.calcsize("<4s"):]
        if not re.match(r"[\w.*]+", key):
            print ">>> Error: %s is not a valid key. Object %i is corrupted." % (repr(key), num)
            break
        
        # Unpack its size.
        try:
            val_len = int(struct.unpack_from("<H", buf)[0])
        except struct.error as err:
            print ">>> Warning: Object %i truncated." % num
            break
        buf = buf[struct.calcsize("<H"):]
        
        # Determine the format string for the value.
        if key in dbl_keys and val_len == 8:
            fmt = "<d"
        elif (key in int_keys or key in dbl_keys or key in bool_keys) and \
                val_len == 4:
            fmt = "<i"
        elif key in ints_keys:
            fmt = "<%ii" % (val_len / 4)
        elif key in dbls_keys:
            fmt = "<%id" % (val_len / 8)
        else:
            fmt = "<%is" % val_len
        #val = struct.unpack_from(fmt, buf)[0]
        
        # Unpack the value.
        try:
            val = struct.unpack_from(fmt, buf)
            if key not in ints_keys and key not in dbls_keys:
                val = val[0]
        except struct.error as err:
            print ">>> Error: Object %i is corrupted." % num
            print ">>> \tKeys so far:", data.keys()
            break
        buf = buf[struct.calcsize(fmt):]
        
        # Format the value.
        if type(val) is str and val and val[-1] == "\x00":
            val = val[:-1]
        if key in bool_keys:
            val = bool(val)
        #elif key in int_keys:
        #    try:
        #        val = int(ord(val or "\x00"))
        #    except TypeError as err:
        #        print ">>> Warning: Non-integer %s set for field %s." % (repr(val), key)
        elif key in url_keys:
            URLS.add(val)
        elif key in types_keys:
            def s_type(scanner, token): return token
            scanner = re.Scanner([(r"[A-Z0-9]{4}", s_type)])
            val = tuple(scanner.scan(val)[0])
        
        # Add the value to the dataset.
        #print "\t", key, val
        data[key] = val
    #print "--"
    
    return data


def print_chunk(num, head, data, parse):
    if parse:
        data = scan_line(num, data)
    else:
        data = repr(data[:70])

    print str(num).zfill(4), head.group(1), head.group(2).zfill(3), data


def main(aer_name, parse):
    wld_name = path.splitext(path.basename(aer_name))[0]
    header = ""

    with open(aer_name, "r") as aer_f:
        header = aer_f.readline()
        aer    = aer_f.read()

        with open(wld_name + ".dat.gz", "wb") as dat_f:
            dat_f.write(aer)

        dat_f = gzip.GzipFile(wld_name + ".dat.gz", "rb")
        dat = dat_f.read()
        dat_f.close()

        with open(wld_name + ".dat", "wb") as dst_f:
            dst_f.write(dat)

        for num, line in enumerate(re.split(r"\n(?=[A-Z0-9]{4}\d)", dat)):
            head = re.match(r"^([A-Z0-9]{4})(\d+):", line)

            if not head:
                print "--"
                continue

            data = line[len(head.group(1) + head.group(2)) + 1:].strip()
            print_chunk(num, head, data, parse)

    print "----"

    URLS.add("./Viewer.png")
    URLS.add("./%s.ctl" % wld_name)

    for url in URLS:
        print url

if __name__ == "__main__":
    try: aer_name = sys.argv[1]
    except: print "usage: %s AER_FILE_NAME <parse>"; sys.exit()

    parse = len(sys.argv) > 2 and sys.argv[2]

    main(aer_name, parse)
