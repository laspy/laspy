#!/usr/bin/env python
import sys
sys.path.append("../")

from laspy import file as File
inFile1 = File.File(sys.argv[1],mode= "r")
inFile2 = File.File(sys.argv[2],mode= "r")

spec = inFile1.reader.point_format.lookup.keys()

def f(x):
    return(list(inFile1.reader.get_dimension(x)) == list(inFile2.reader.get_dimension(x)))

passed = 0
failed = 0
for dim in spec:
    if f(dim):
        passed += 1
        print("Dimension: " + dim + " is identical.")
    else:
        failed += 1
        print("Dimension: " + dim + " is not identical")

print(str(passed) + " identical dimensions out of " + str(passed + failed))
inFile1.close()
inFile2.close()
