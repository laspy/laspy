#!/usr/bin/env python
import sys
import cProfile
sys.path.append("../")

from laspy import file as File
inFile = File.File(sys.argv[1],mode= "r")
outFile = File.File(sys.argv[2],mode= "w", header = inFile.header)

def f(): 
    print("Reading Points")
    points = inFile.get_points()
    print("Writing Points")
    outFile.set_points(points)

#cProfile.run("f()")
f()
#out = []
#pts = 0
#for p in inFile:
#    pts += 1
#    out.append(p.pack())
#    if pts % 10000 == 0:
#        print("Processing Point: " + str(pts))

#outFile.writer._set_raw_points(out)

inFile.close()
outFile.close(ignore_header_changes=True)
