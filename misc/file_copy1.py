#!/usr/bin/env python
import sys
sys.path.append("../")

from laspy import file as File
inFile = File.File(sys.argv[1],mode= "r")
outFile = File.File(sys.argv[2],mode= "w", header = inFile.header)

spec = inFile.reader.point_format.lookup.keys()

def f(x):
    print(x)
    tmp = inFile.reader.get_dimension(x)
    outFile.writer.set_dimension(x, tmp)

map(f, spec)

inFile.close()
outFile.close(ignore_header_changes = True)
