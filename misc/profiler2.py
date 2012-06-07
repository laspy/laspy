#!/usr/bin/env python
import sys
import cProfile
sys.path.append("../")

from laspy import file as File
inFile = File.File(sys.argv[1],mode= "r")
outFile = File.File(sys.argv[2],mode= "w", header = inFile.header)

print("Number of points to be copied: " + str(len(inFile)))
spec = inFile.reader.point_format.lookup.keys()

def f(x):
    print("outFile." + str(x)+" = "+"inFile." + str(x))
    outFile.writer.set_dimension(x, inFile.reader.get_dimension(x))

def z():
    map(f, spec)
    inFile.close()
    outFile.close(ignore_header_changes = True)

cProfile.run("z()")
