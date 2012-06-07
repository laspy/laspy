#!/usr/bin/env python
import sys
from multiprocessing import Process
sys.path.append("../")

from laspy import file as File
inFile = File.File(sys.argv[1],mode= "r")
outFile = File.File(sys.argv[2],mode= "w", header = inFile.header)
outFile.writer.pad_file_for_point_recs(len(inFile))
outFile.close(ignore_header_changes =True)
spec = inFile.reader.point_format.lookup.keys()

def write_dimension(dimname, dimdata):
    file_view = File.File(sys.argv[2], mode = "rw")
    file_view.writer.set_dimension(dimname, dimdata)
    file_view.close(ignore_header_changes = True)

processes = []

for dimname in spec:
    print(dimname)
    dataList = list(inFile.reader.get_dimension(dimname))
    p = Process(target=write_dimension, args=(dimname, dataList))
    p.start()
    processes.append(p)

for p in processes:
    p.join()

#def f(x):
#    print("outFile." + str(x)+" = "+"inFile." + str(x))
#    outFile.writer.set_dimension(x, inFile.reader.get_dimension(x))

#map(f, spec)

inFile.close()


