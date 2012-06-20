import sys
sys.path.append("../")

from laspy import file as File
from laspy import header
from laspy import util

inFile = File.File(sys.argv[1],mode= "r")

new_header = inFile.header.get_copy()
new_header.format = util.Format("h1.1")
new_header.pt_dat_format_id = 0
outFile = File.File(sys.argv[2],mode= "w",vlrs = inFile.header.vlrs, header = new_header)

for dim in inFile.reader.point_format.specs:
    print("Copying dimension: " + dim.name)
    in_dim = inFile.reader.get_dimension(dim.name)
    try:
        outFile.writer.set_dimension(dim.name, in_dim)
    except(util.LaspyException):
        print("Couldn't set dimension: " + dim.name + 
                " with file format " + str(outFile.header.version) + 
                ", and point_format " + str(outFile.header.data_format_id))


