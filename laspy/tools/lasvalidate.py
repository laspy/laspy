from laspy.file import File
import numpy as np
import argparse
import logging

class validate():
    def __init__(self):
        self.parse_args()
   
    def parse_args(self):        
        parser = argparse.ArgumentParser(description="""Accept the path to a .LAS file, 
                                                    and print a list of point records 
                                                    with invalid (X,Y,Z) information.""")

        parser.add_argument("in_file", metavar="Input File", type = str, nargs=1, help = "Path to input file")
        parser.add_argument("-log", metavar="Log File", type = str, nargs=1, help ="Path to log file", default = "lasvalidate.log")
        self.args = parser.parse_args()


    def validate(self):
        print("Reading in file: " + self.args.in_file[0])
        inFile = File(self.args.in_file[0], mode = "r")

        print("Test 1: Checking header bounding box: ")
        bb = zip(["X", "Y", "Z"], inFile.header.min, inFile.header.max)
        print("...Header bounding box:")
        for i in bb:
            print("..." + str(i))

        X_invalid = np.logical_or((inFile.header.min[0] > inFile.x), (inFile.header.max[0] < inFile.x))
        Y_invalid = np.logical_or((inFile.header.min[1] > inFile.y), (inFile.header.max[1] < inFile.y))
        Z_invalid = np.logical_or((inFile.header.min[2] > inFile.z), (inFile.header.max[2] < inFile.z))

        bad_indices = np.where(np.logical_or(X_invalid, Y_invalid, Z_invalid))
        if len(bad_indices[0] == 0):
            print("...Header bounding box errors detected.")
            if len(bad_indices[0]) == len(inFile):
                print("...All points outside bounding box.")
            else:
                print("...printing bad indices to log: " + self.args.log)
                for i in bad_indices[0]:
                    logging.info("Point outside header bounding box: %i" % i)
        else:
            print("...passed.")

def main():
    validator = validate()  
    logging.basicConfig(filename=validator.args.log,level=logging.DEBUG)
    validator.validate()


