#!/usr/bin/env python
import sys
sys.path.append("../")

from laspy import file as File
inFile = File.File(sys.argv[1],mode= "r")
outFile = File.File(sys.argv[2],mode= "w", header = inFile.header)
cls =sys.argv[3].split(",")
spec = inFile.reader.point_format.lookup.keys()

in_cls = inFile.reader.get_raw_classification()
out_cls = [x in cls for x in in_cls]
npts = sum(out_cls)
outFile.writer.pad_file_for_point_recs(npts)
outFile.writer.seek(outFile.header.data_offset, rel = False)
for i in xrange(npts):
    if out_cls[i]:
        outFile.writer.data_provider._mmap.write(inFile.get_raw_point(index))

inFile.close()
outFile.close(ignore_header_changes = True)
