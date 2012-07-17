from laspy.file import File
from laspy.util import Format
import argparse

parser = argparse.ArgumentParser(description='Accept \"in_file\" and \"out_file\" .LAS files, and convert from \"in_file\" to \"out_file\" according to \"point_format\" and \"file_version\".')
parser.add_argument('in_file', metavar='in_file', type=str, nargs='+',
                           help='input file path')
parser.add_argument('out_file', metavar='out_file', type=str, nargs='+',
                           help='output file path')
parser.add_argument('point_format', metavar='point_format', type=int, nargs='+',
                           help='output point format (0-10)')
parser.add_argument('file_version', metavar='file_version', type=str, nargs='+',
                            help='output file version 1.0-1.4')
parser.add_argument('-u', type=bool,help="Update the header histogram? (slow)", default=False)


args = parser.parse_args()
update_histogram = args.u

## Try to open in_file in read mode. 

file_version = args.file_version[0]
point_format = args.point_format[0]
try:
    inFile = File(args.in_file[0], mode = "r")
except Exception, error:
    print("There was an error reading in the input file: ")
    print(error)
    quit()


## Verify that the user has supplied a compatable point_format and file_version.
if not (point_format in range(11)):
    raise Exception("Invalid point format: %i" % point_format)
if (point_format > 5 and file_version !="1.4"):
    raise Exception("Point formats 6-10 are only supported by LAS version 1.4 files.")
if (point_format > 3 and not (file_version in ["1.3", "1.4"])):
    raise Exception("Point format %i is not available for file version %s" % (point_format, file_version))
if (point_format >= 2 and not (file_version in ["1.2", "1.3", "1.4"])):
    raise Exception("Point format %i is not available for file version %s" % (point_format, file_version))

old_file_version = inFile.header.version
old_point_format = inFile.header.data_format_id
print("Converting from file version %s to version %s." %(old_file_version, file_version)) 
print("Converting from point format %i to format %i."%(old_point_format, point_format))


try:
    new_header = inFile.header.copy()
    new_header.format = file_version 
    new_header.data_format_id = point_format

    old_data_rec_len = new_header.data_record_length
    old_std_rec_len = Format(old_point_format).rec_len
    diff =   old_data_rec_len - old_std_rec_len
    if (diff > 0):
        print("Extra Bytes Detected.")

    new_header.data_record_length = Format(point_format).rec_len + ((diff > 0)*diff)
    evlrs = inFile.header.evlrs
    if file_version != "1.4" and old_file_version == "1.4":
        print("Warning: input file has version 1.4, and output file does not. This may cause trunctation of header data.")
        new_header.point_return_count = inFile.header.legacy_point_return_count
        new_header.point_records_count = inFile.header.legacy_point_records_count
    if not (file_version in ["1.3", "1.4"]) and old_file_version in ["1.3", "1.4"]:
        print("Stripping any EVLRs")
        evlrs = []
    if (file_version == "1.3" and len(inFile.header.evlrs) > 1):
        print("Too many EVLRs for format 1.3, keeping the first one.")
        evlrs = inFile.header.evlrs[0]
    outFile = File(args.out_file[0], header = new_header, mode = "w", vlrs = inFile.header.vlrs, evlrs = evlrs)
    if outFile.point_format.rec_len != outFile.header.data_record_length:
        pass
except Exception, error:
    print("There was an error instantiating the output file.")
    print(error)
    quit()

try:
    for dimension in inFile.point_format.specs:
        if dimension.name in outFile.point_format.lookup:
            outFile.writer.set_dimension(dimension.name, inFile.reader.get_dimension(dimension.name))
            print("Copying: " + dimension.name)
except Exception, error:
    print("Error copying data.")
    print(error)
    quit()


inFile.close()
outFile.close(ignore_header_changes = not update_histogram)


