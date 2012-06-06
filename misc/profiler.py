#!/usr/bin/env python
import sys
import cProfile
sys.path.append("../")

from laspy import file as File
inFile = File.File(sys.argv[1],mode= "r")
print("File length: " + str(len(inFile)) + " points to be copied.")
outFile = File.File(sys.argv[2],mode= "w", header = inFile.header)

spec = inFile.reader.point_format.lookup.keys()

def f():
    outFile.X = inFile.X
    outFile.Y = inFile.Y

cProfile.run("f()")

#for x in spec:
#    print(x)
#    outFile.writer.set_dimension(x, inFile.reader.get_dimension(x))


inFile.close()
outFile.close()
