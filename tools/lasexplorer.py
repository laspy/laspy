import argparse
from laspy.file import File
parser =argparse.ArgumentParser(description = """Open a file in read mode and
                                print a simple description.""")
parser.add_argument("in_file", metavar = "in_file", 
                    type=str,nargs="+",help = "LAS file to explore")
parser.add_argument("-mode",metavar="file mode", type=str,default="r", 
        help = "Mode, default is r. Acceptable values: (r, rw)")
parser.add_argument("-q", metavar="quiet", type=bool, default=False, 
        help ="Skip summary? (default false)")

args = parser.parse_args()
print(args)
# Check mode
if args.mode =="rw":
    print("Mode = %s, changes to file will be committed to disk." % args.mode)
elif args.mode != "r":
    print("Warning: invalud mode: " + args.mode)

# Try to read in file
print("Reading: " + args.in_file[0])
try:
    inFile = File(args.in_file[0], mode = args.mode)
    READ_SUCCESS = True
    print("Read successful, file object is called inFile")
except Exception, error:
    print("Error while reading file:")
    print(error)
    READ_SUCCESS = False

# If we have a file and user wants verbose, print summary.

if READ_SUCCESS and not args.q:
    print("LAS File Summary:")
    print("File Version: " + str(inFile.header.version))
    print("Point Format: " + str(inFile.header.data_format_id))
    print("Number of Point Records: " + str(len(inFile)))
    print("Point Dimensions: ")
    for dim in inFile.point_format:
        print("    " + dim.name)




