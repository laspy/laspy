from laspy.file import  File
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

args = parser.parse_args()

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
if (point_format > 2 and not (file_version in ["1.2", "1.3", "1.4"])):
    raise Exception("Point format %i is not available for file version %s" % (point_format, file_version))

old_file_version = inFile.header.version
old_point_format = inFile.header.data_format_id
print("Converting from file version %s to version %s." %(old_file_version, file_version)) 
print("Converting from point format %i to format %i."%(old_point_format, point_format))


