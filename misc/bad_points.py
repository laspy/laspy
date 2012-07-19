from laspy.file import File
import numpy as np
import argparse

parser = argparse.ArgumentParser(description="""Accept the path to a .LAS file, 
                                                and print a list of point records 
                                                with invalid (X,Y,Z) information.""")

parser.add_argument("in_file", metavar="Input File", type = str, nargs=1, help = "Path to input file")

args = parser.parse_args()

inFile = File(args.in_file[0], mode = "r")
X_invalid = np.logical_or((inFile.header.min[0] > inFile.x), (inFile.header.max[0] < inFile.x))
Y_invalid = np.logical_or((inFile.header.min[1] > inFile.y), (inFile.header.max[1] < inFile.y))
Z_invalid = np.logical_or((inFile.header.min[2] > inFile.z), (inFile.header.max[2] < inFile.z))

bad_indices = np.where(np.logical_or(X_invalid, Y_invalid, Z_invalid))
print("Array bad_indices: ")
print(bad_indices)



