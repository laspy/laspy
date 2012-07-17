import sys
from laspy import util
from laspy import file as File
import argparse

parser = argparse.ArgumentParser(description='Compare LAS files file_1 and file_2 by dimension, header field, vlr and evlr.')
parser.add_argument('file_1', metavar='file_1', type=str, nargs='+',
                    help='LAS file 1 path.')
parser.add_argument('file_2', metavar='file_2', type=str, nargs='+',
                    help='LAS file 2 path.')

args = parser.parse_args()

print(args)
file_1 = args.file_1[0]
file_2 = args.file_2[0]

try:
    inFile1 = File.File(file_1,mode= "r")
    inFile2 = File.File(file_2,mode= "r")
except Exception, error:
    print("Error reading in files:")
    print(error)
    quit()

def f(x):
    try:
        return(list(inFile1.reader.get_dimension(x)) == list(inFile2.reader.get_dimension(x)))
    except:
        if not (x in inFile1.point_format.lookup) and (x in inFile2.point_format.lookup):
            print("Dimension %s: NOT PRESENT IN FILE 1" % x)
        elif not (x in inFile2.point_format.lookup) and (x in inFile1.point_format.lookup):
            print("Dimension %s: NOT PRESENT IN FILE 2" % x)
        else:
            print("THERE WAS AN ERROR COMPARING DIMENSION %s" + str(x))
        return(False)

def g(x):
    try:
        return(inFile1.reader.get_header_property(x) == inFile2.reader.get_header_property(x))
    except:
        if not (x in inFile1.header.header_format.lookup) and (x in inFile2.header.header_format.lookup):
            print("HEADER PROPERTY %s NOT PRESENT IN FILE 1.")
        elif not (x in inFile2.header.header_format.lookup) and (x in inFile1.header.header_format.lookup):
            print("HEADER PROPERTY %s NOT PRESENT IN FILE 2.")
        else:
            print("THERE WAS AN ERROR COMPARING HEADER PROPERTY: %s" + str(x))
        return(False)

print("Testing Header")
try:
    passed = 0
    failed = 0
    for item in inFile1.reader.header_format.specs:
        if g(item.name):
            print("Header Field: " + item.name + " ...identical.")
            passed += 1
        else:
            print("Header Field " + item.name + " ...DIFFERENT.")
            print("   File 1: " + str(inFile1.reader.get_header_property(item.name)))
            print("   File 2: " + str(inFile2.reader.get_header_property(item.name)))
            failed += 1
    print("%i of %i header fields match." % (passed, passed + failed))
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
        print("Dimension " + dim + ": identical.")
    else:
        failed += 1
        print("Dimension " + dim + ": differs")

print(str(passed) + " identical dimensions out of " + str(passed + failed))
inFile1.close()
inFile2.close()
