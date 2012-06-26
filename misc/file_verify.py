#!/usr/bin/env python
import sys
sys.path.append("../")
from laspy import util
from laspy import file as File
inFile1 = File.File(sys.argv[1],mode= "r")
inFile2 = File.File(sys.argv[2],mode= "r")



def f(x):
    try:
        return(list(inFile1.reader.get_dimension(x)) == list(inFile2.reader.get_dimension(x)))
    except:
        print("There was a problem comparing dimension " + str(x))
        return(False)
def g(x):
    try:
        return(inFile1.reader.get_header_property(x) == inFile2.reader.get_header_property(x))
    except:
        print("There was a problem comparing header property: " + str(x))
        return(False)


print("Testing Header")
try:
    for item in inFile1.reader.header_format.specs:
        if g(item.name):
            print("Header Field " + item.name + " is identical.")
        else:
            print("Header Field " + item.name + " differs.")
            print("   File 1: " + str(inFile1.reader.get_header_property(item.name)))
            print("   File 2: " + str(inFile2.reader.get_header_property(item.name)))
except:
    print("There was a problem comparing headers.")

def checkVLR(specname, vlr1, vlr2):
    return(vlr1.__dict__[specname] == vlr2.__dict__[specname])
    

print("Testing VLRs")
try:
    for i in xrange(len(inFile1.reader.vlrs)):
        vlr1 = inFile1.reader.vlrs[i]
        vlr2 = inFile2.reader.vlrs[i]
        for spec in util.Format("VLR").specs:
            if checkVLR(spec.name, vlr1, vlr2):
                print("vlr # " + str(i) + ", field: " + spec.name + " is identical.")
            else:
                print("vlr # " + str(i) + ", field: " + spec.name + " differs,")
        if vlr1.VLR_body == vlr2.VLR_body:
            print("vlr # " + str(i) + ", field: Body is identical.")
        else:
            print("vlr # " + str(i) + ", field: Body differs.")
except:
    print("There was a problem comparing vlrs.")

print("Checking EVLRs")
try:
    for i in xrange(len(inFile1.header.evlrs)):
        vlr1 = inFile1.header.evlrs[i].to_byte_string()
        vlr2 = inFile1.header.evlrs[i].to_byte_string()
        if vlr1 == vlr2:
            print("EVLRs are identical.")
        else:
            print("EVLRs differ.")
except:
    print("There was a problem comparing EVLRs")

spec = inFile1.reader.point_format.lookup.keys()
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
