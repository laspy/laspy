import sys
sys.path.append("../")

from laspy import file
try:
    inFile = open("../test/data/simple.las", "r")
    inData = inFile.read()
    outFile = open("../test/.temp.las", "w")
    outFile.write(inData)
    outFile.close()
    inFile.close()
    file_ = file.File("../test/.temp.las")
    print("Temporary las file created from ./test/data/simple.las")    
    print("File object for .temp.las created, named file_")
    print("Have fun!")
except(Exception):
    print("Something broke, sorry.")

