#!/usr/bin/env python
import sys
sys.path.append("../")

from laspy import file as File
inFile = File.File(sys.argv[1],mode= "r")
outFile = File.File(sys.argv[2],mode= "w", header = inFile.header)
cls =[int(x) for x in sys.argv[3].split(",")]

in_cls = inFile.reader.get_raw_classification()
out_cls = [x in cls for x in in_cls]
npts = sum(out_cls)
print(str(npts) + " out of " + str(len(out_cls)) + " have classification in " + str(cls))
outFile.writer.pad_file_for_point_recs(npts)
outFile.writer.seek(outFile.header.data_offset, rel = False)
prefs = [inFile.reader.point_refs[i] for i in xrange(npts) if out_cls[i]]
reclen = inFile.header.data_record_length

for i in xrange(npts):
    inFile.reader.seek(prefs[i], rel = False)
    outFile.writer.data_provider._mmap.write(inFile.reader.data_provider._mmap.read(reclen))    

#outFile.writer.data_provider._mmap.write(inFile.reader.get_raw_point(i))

inFile.close()
outFile.close(ignore_header_changes = True)
