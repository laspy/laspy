#!/usr/bin/env python
import sys
sys.path.append("../")
from laspy import util
from laspy import file as File
inFile1 = File.File(sys.argv[1],mode= "r")
inFile2 = File.File(sys.argv[2],mode= "r")

spec = inFile1.reader.point_format.lookup.keys()

def f(x):
    return(list(inFile1.reader.get_dimension(x)) == list(inFile2.reader.get_dimension(x)))
def g(x):
    return(inFile1.reader.get_header_property(x) == inFile2.reader.get_header_property(x))


print("Testing Header")
for item in inFile1.reader.header_format.specs:
    if g(item.name):
        print("Header Field " + item.name + " is identical.")
    else:
        print("Header Field " + item.name + " differs.")
        print("   File 1: " + str(inFile1.reader.get_header_property(item.name)))
        print("   File 2: " + str(inFile2.reader.get_header_property(item.name)))

def checkVLR(specname, vlr1, vlr2):
    return(vlr1.__dict__[specname] == vlr2.__dict__[specname])
    

print("Testing VLRs")
for i in xrange(len(inFile1.reader.vlrs)):
    vlr1 = inFile1.reader.vlrs[i]
    vlr2 = inFile2.reader.vlrs[i]
    for spec in util.Format("VLR"):
        if checkVLR(spec.name, vlr1, vlr2):
            print("vlr # " + str(i) + ", field: " + spec.name + "is identical.")
        else:
            print("vlr # " + str(i) + ", field: " + spec.name + "differs,")


print("Testing Dimensions")
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
