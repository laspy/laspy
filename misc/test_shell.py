#!/usr/bin/env python
import sys
sys.path.append("../")

from laspy import file
inFile = open(sys.argv[1], "r")
inData = inFile.read()
outFile = open(sys.argv[2], "w")
outFile.write(inData)
outFile.close()
inFile.close()
file_ = file.File(sys.argv[2], mode = "rw")
