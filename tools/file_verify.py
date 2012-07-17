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

def print_title(string):
    print("#"*65)
    print("#  " + string + " "*(65 - (len(string) + 4)) + "#")
    print("#"*65)


def f(x):
    try:
        return(list(inFile1.reader.get_dimension(x)) == list(inFile2.reader.get_dimension(x)))
    except:
        outstr = "Dimension: %s" %x
        outstr += " "*(50-len(outstr))
        if not (x in inFile1.point_format.lookup) and (x in inFile2.point_format.lookup):
            print(outstr + "Not present in file_1.")
        elif not (x in inFile2.point_format.lookup) and (x in inFile1.point_format.lookup):
            print(outstr + "Not present in file_2.")
        else:
            print("There was an error comparing dimension: %s" + str(x))
        return(False)

def g(x):
    try:
        return((1*(inFile1.reader.get_header_property(x) == inFile2.reader.get_header_property(x))))
    except:
        outstr = "Header Property: %s" % x
        outstr += (" "*(50-len(outstr)))
        if not (x in inFile1.header.header_format.lookup) and (x in inFile2.header.header_format.lookup):
            print(outstr + "Not present in file_1.")
        elif not (x in inFile2.header.header_format.lookup) and (x in inFile1.header.header_format.lookup):
            print(outstr + "Not present in file_2.")
        else:
            print("There was an error while comparing header property: %s" + str(x))
        return(2)

print_title("Checking Headers")
try:
    passed = 0
    failed = 0
    header_props = set()
    for item in inFile1.reader.header_format.specs:
        header_props.add(item.name)
    for item in inFile2.reader.header_format.specs:
        header_props.add(item.name)
    for item in header_props:
        outstr = "Header Property: %s" % item
        outstr += " "*(50-len(outstr))
        result = g(item)
        if result == 1:
            print(outstr + "identical")
            passed += 1
        elif not result == 2:
            print(outstr + "different")
            print("   File 1: " + str(inFile1.reader.get_header_property(item)))
            print("   File 2: " + str(inFile2.reader.get_header_property(item)))
            failed += 1
    print("%i of %i header fields match." % (passed, passed + failed))
except:
    print("There was an error while comparing headers. ")

def checkVLR(specname, vlr1, vlr2):
    return(vlr1.__dict__[specname] == vlr2.__dict__[specname])
    

print_title("Checking VLRs")

try:
    if len(inFile1.header.vlrs) != len(inFile2.header.vlrs):
        print("Number of VLRs differs: file_1 has %i and file_2 has %i. Comparing where possible..."
                % (len(inFile1.header.vlrs), len(inFile2.header.vlrs)))
    for i in xrange(min(len(inFile1.header.vlrs), len(inFile2.header.vlrs))):
        outstr = "VLR Record: %i" %i
        outstr += " "*(50 - len(outstr))
        vlr1 = inFile1.header.vlrs[i].to_byte_string()
        vlr2 = inFile2.header.vlrs[i].to_byte_string()
        if vlr1 == vlr2:
            print(outstr + "identical")
        else:
            print(outstr + "different")
except:
    print("There was a problem comparing VLRs")

print_title("Checking EVLRs")
try:
    if len(inFile1.header.evlrs) != len(inFile2.header.evlrs):
        print("Number of VLRs differs: file_1 has %i and file_2 has %i. Comparing where possible..."
                % (len(inFile1.header.evlrs), len(inFile2.header.evlrs)))

    for i in xrange(min(len(inFile1.header.evlrs), len(inFile2.header.evlrs))):
        outstr = "EVLR Record: %i" %i
        outstr += " "*(50 - len(outstr))
        vlr1 = inFile1.header.evlrs[i].to_byte_string()
        vlr2 = inFile1.header.evlrs[i].to_byte_string()
        if vlr1 == vlr2:
            print(outstr + "identical")
        else:
            print(outstr + "different")
except:
    print("There was a problem comparing EVLRs")

dims = set()
for item in inFile1.reader.point_format.lookup.keys():
    dims.add(item)
for item in inFile2.reader.point_format.lookup.keys():
    dims.add(item)
print_title("Checking Dimensions")
passed = 0
failed = 0
for dim in dims:
    outstr = "Dimension: %s" % dim 
    outstr += " "*(50-len(outstr))
    if f(dim):
        passed += 1
        print(outstr +  "identical")
    else:
        failed += 1
        print(outstr + "different")

print(str(passed) + " identical dimensions out of " + str(passed + failed))
inFile1.close()
inFile2.close()
