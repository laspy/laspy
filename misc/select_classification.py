#!/usr/bin/env python
import sys
import numpy as np
import cProfile

def f():
    sys.path.append("../")
    
    from laspy import file as File
    inFile = File.File(sys.argv[1],mode= "r")
    outFile = File.File(sys.argv[2],mode= "w", header = inFile.header)
    cls =[int(x) for x in sys.argv[3].split(",")]
    #outFile.writer.set_padding(outFile.header.data_offset)

    vf = np.vectorize(lambda x: x in cls)
    print("Writing")
    outData = inFile.reader.get_points()[vf(inFile.raw_classification)]
    outFile.writer.set_points(outData)
    #outFile.writer.data_provider._mmap.write(inFile.reader.get_raw_point(i))
    print("Closing")
    inFile.close()
    outFile.close(ignore_header_changes = True)

#cProfile.run("f()")
f()
