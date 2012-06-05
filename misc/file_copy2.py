#!/usr/bin/env python
import sys
sys.path.append("../")

from laspy import file as File
inFile = File.File(sys.argv[1],mode= "r")
outFile = File.File(sys.argv[2],mode= "w", header = inFile.header)

spec = inFile.reader.point_format.lookup.keys()
print("Reading Points")
out = []
pts = 0
for p in inFile:
    pts += 1
    out.append(p.pack())
    if pts % 10000 == 0:
        print("Processing Point: " + str(pts))

print("Writing Points")
outFile.writer._set_raw_points(packedPoints)

inFile.close()
outFile.close()
