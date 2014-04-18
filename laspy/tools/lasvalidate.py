import laspy
import numpy as np
import argparse
import logging

class validate():
    def __init__(self):
        self.parse_args()
        self.clear_log()
        self.errors = 0
        self.tests = 0

    def parse_args(self):        
        parser = argparse.ArgumentParser(description="""Accept the path to a .LAS file, 
                                                    and print a list of point records 
                                                    with invalid (X,Y,Z) information.""")

        parser.add_argument("in_file", metavar="Input File", type = str, nargs=1, help = "Path to input file")
        parser.add_argument("--log", metavar="Log File", type = str, nargs=1, help ="Path to log file", default = "lasvalidate.log")
        parser.add_argument("--tol", metavar="Tolerance", type = float, nargs = 1, help = "Tolerance for header max/min vs actual max/min comparisons.", default = 0.01)
        self.args = parser.parse_args()

    def clear_log(self):
        tmp = open(self.args.log, "w")
        tmp.close()

    def bb(self,inFile, xval, yval, zval):
        X_invalid = np.logical_or((inFile.header.min[0] > xval), (inFile.header.max[0] < xval))
        Y_invalid = np.logical_or((inFile.header.min[1] > yval), (inFile.header.max[1] < yval))
        Z_invalid = np.logical_or((inFile.header.min[2] > zval), (inFile.header.max[2] < zval))

        bad_indices = np.where(np.logical_or(X_invalid, Y_invalid, Z_invalid))
        return(bad_indices)

    def test0(self, inFile):
        print("Test 0: Does this look like a LAS file?")
        if inFile.header.file_signature != "LASF":
            logging.info("Incorrect File Signature")
            print("... failed")
            self.errors += 1
        if self.errors == 0:
            print("...passed")
        self.tests += 1


    def test1(self, inFile):
        print("Test 1: Checking that all points fall inside header bounding box: ")
        bb = zip(["X", "Y", "Z"], inFile.header.min, inFile.header.max)
        print("... Header bounding box:")
        for i in bb:
            print("..." + str(i))

        bad_indices = self.bb(inFile, inFile.x, inFile.y, inFile.z)

        if len(bad_indices[0] == 0):
            print("... Header bounding box errors detected.")
            if len(bad_indices[0]) == len(inFile):
                new_bi = self.bb(inFile, inFile.X, inFile.Y, inFile.Z)[0]
                if len(new_bi) < len(inFile):
                    print("... Using unscaled values gives fewer invalid points: " + str(len(new_bi)) + ", header appears to use unscaled data.")
                    logging.info("Header appears to use unscaled data in max/min. This may follow spec, but is less common than using scaled data. ")
                else:
                    print("... Bounding box appears to be invalid.")
                    logging.info("Bounding box appears to be invalid.")
                    
            else:
                print("... printing bad indices to log: " + self.args.log)
                for i in bad_indices[0]:
                    logging.info("Point outside header bounding box: %i" % i)
            self.errors += 1
        else:
            print("... passed.")
        self.tests += 1

    def test2(self, inFile):
        print("Test 2: Checking that header bounding box is precise.")
        actual_max = [np.max(vec) for vec in [inFile.x, inFile.y, inFile.z]]
        actual_min = [np.min(vec) for vec in [inFile.x, inFile.y, inFile.z]]
        header_max = inFile.header.max 
        header_min = inFile.header.min
        max_diffs = [actual_max[i] - header_max[i] for i in range(3)]
        min_diffs = [actual_min[i] - header_min[i] for i in range(3)]
        err = 0
        for i in range(len(max_diffs)):
            if max_diffs[i] > self.args.tol:
                err += 1
                print("... " + ["X", "Y", "Z"][i] + " header max doesn't match actual max.")
                print("...    actual max: " + str(actual_max[i]) + ", header max: " + str(header_max[i]))
                logging.info(["X", "Y", "Z"][i] + " header max doesn't match actual max at tolerance %s." %str(self.args.tol))
        for i in range(len(min_diffs)):
            if min_diffs[i] > self.args.tol:
                err += 1
                print("... " + ["X", "Y", "Z"][i] + " header min doesn't match actual min.")
                print("...    actual min: " + str(actual_max[i]) + ", header min: " + str(header_max[i]))
                logging.info(["X", "Y", "Z"][i] + " header min doesn't match actual min at tolerance %s." %str(self.args.tol))
        if err == 0:
            print("... passed")
        else:
            self.errors += 1
            print("... failed")
        self.tests += 1

    def test3(self, inFile):
        print("Test 3: Checking that X and Y range values are reasonable.")
        X_range = np.max(inFile.x) - np.min(inFile.x)
        Y_range = np.max(inFile.y) - np.min(inFile.y)
        err = 0
        if X_range > 2000:
            err += 1
            print("... X range may be unreasonable: " + str(X_range))
            logging.info("X range may be unreasonable: " + str(X_range))
        if Y_range > 2000:
            err += 1
            print("... Y range may be unreasonable: " + str(Y_range))
            logging.info("Y range may be unreasonable: " + str(Y_range))
        if err == 0:
            print("... passed")
        else:
            print("... failed")
            self.errors += 1
        self.tests += 1

    def validate(self):
        print("Reading in file: " + self.args.in_file[0])
        inFile = laspy.file.File(self.args.in_file[0], mode = "r")
        self.test0(inFile)
        self.test1(inFile)
        self.test2(inFile)
        self.test3(inFile)
        print(str(self.errors) + " errors out of " + str(self.tests) + " tests")


def main():
    validator = validate()  
    logging.basicConfig(filename=validator.args.log,level=logging.DEBUG)
    validator.validate()


