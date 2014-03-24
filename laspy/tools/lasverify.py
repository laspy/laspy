import laspy
import argparse

class lasverify():
    def __init__(self):
        self.parse_args()
        self.verify()
        ## Setup argparse to accept command line arguments
    def parse_args(self):
        parser = argparse.ArgumentParser(
                description='''Compare LAS files file_1 and file_2 by dimension, header
                       field, vlr and evlr.''')
        parser.add_argument('file_1', metavar='file_1', type=str, nargs='+',
                            help='LAS file 1 path.')
        parser.add_argument('file_2', metavar='file_2', type=str, nargs='+',
                            help='LAS file 2 path.')

        parser.add_argument('-b', type=bool,help='''Attempt to compare incompatable 
                sub-byte sized data fields if present? (slow)''', default=False)

        self.args = parser.parse_args()

    def verify(self):
    ## Set global varibles for convenience.
        file_1 = self.args.file_1[0]
        file_2 = self.args.file_2[0]
        PRESERVE = self.args.b 

    ## Try to open both files in read mode.
        try:
            inFile1 = laspy.file.File.File(file_1,mode= "r")
            inFile2 = laspy.file.File.File(file_2,mode= "r")
        except Exception, error:
            print("Error reading in files:")
            print(error)
            quit()

    ## Set global flag to indicate whether we need to look at incompatable 
    ## bit field bytes. 
        SUB_BYTE_COMPATABLE = ((inFile1.header.data_format_id <= 5) == 
                            (inFile2.header.data_format_id <= 5)) 

    ## Warn the user if they chose not to check incompatable point formats.
        if (not SUB_BYTE_COMPATABLE) and (not PRESERVE):
            print("""WARNING: Point formats %i and %i have mismatched sub-byte fields. 
                    The default behavior in this case is to ignore these fields during 
                    the file_verify procedure. If you want laspy to attempt to match up
                    sub-byte data between these two formats, specify -b=True 
                    (this might take some time depending on the size of the file)""")

        def print_title(string):
            print("#"*65)
            print("#  " + string + " "*(65 - (len(string) + 4)) + "#")
            print("#"*65)

    ## Define convenience function to try to compare point dimensions. 
        def f(x):
            try:
                return(1*(list(inFile1.reader.get_dimension(x)) == list(inFile2.reader.get_dimension(x))))
            except:
                outstr = "Dimension: %s" %x
                outstr += " "*(50-len(outstr))
                if not (x in inFile1.point_format.lookup) and (x in inFile2.point_format.lookup):
                    print(outstr + "not present in file_1.")
                elif not (x in inFile2.point_format.lookup) and (x in inFile1.point_format.lookup):
                    print(outstr + "not present in file_2.")
                else:
                    print("There was an error comparing dimension: %s" + str(x))
                return(2)

    ## Define convenience function to try to compare header fields. 
        def g(x):
            try:
                return((1*(inFile1.reader.get_header_property(x) == inFile2.reader.get_header_property(x))))
            except:
                outstr = "Header Property: %s" % x
                outstr += (" "*(50-len(outstr)))
                if not (x in inFile1.header.header_format.lookup) and (x in inFile2.header.header_format.lookup):
                    print(outstr + "not present in file_1.")
                elif not (x in inFile2.header.header_format.lookup) and (x in inFile1.header.header_format.lookup):
                    print(outstr + "not present in file_2.")
                else:
                    print("There was an error while comparing header property: %s" + str(x))
                return(2)

    ## Build union fo header fields, then check them.
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

    ## Check VLRs
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

    ## Check EVLRs
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

    ## Build a union of dimensions in each file, then compare them.
        dims = set()
        for item in inFile1.reader.point_format.lookup.keys():
            dims.add(item)
        for item in inFile2.reader.point_format.lookup.keys():
            dims.add(item)
        print_title("Checking Dimensions")
        passed = 0
        failed = 0
        for dim in dims:
            if not SUB_BYTE_COMPATABLE and dim in ("raw_classification","classification_flags", "classification_byte", "flag_byte"):
                continue
            outstr = "Dimension: %s" % dim 
            outstr += " "*(50-len(outstr))
            result = f(dim)
            if result == 1:
                passed += 1
                print(outstr +  "identical")
            elif result != 2:
                failed += 1
                print(outstr + "different")

        def print_sb(string, result):
            outstr  ="Sub-byte field: " + string
            outstr += " "*(50-len(outstr))
            if result:
                print(outstr + "identical")
                return(1)
            else:
                print(outstr + "different")
                return(0)

    ## If we need to, compare valid sub-byte fields
        sb_total = 0
        if not SUB_BYTE_COMPATABLE and PRESERVE:
            print("Comparing sub-byte fields (this might take awhile)")
            sb_total += print_sb("classification", all(inFile1.classification == inFile2.classification)) 
            sb_total += print_sb("return_num", all(inFile1.return_num == inFile2.return_num))
            sb_total += print_sb("num_returns", all(inFile1.num_returns == inFile2.num_returns))
            sb_total += print_sb("scan_dir_flag", all(inFile1.scan_dir_flag == inFile2.scan_dir_flag))
            sb_total += print_sb("edge_flight_line", all(inFile1.edge_flight_line == inFile2.edge_flight_line))
            sb_total += print_sb("synthetic", all(inFile1.synthetic == inFile2.synthetic))
            sb_total += print_sb("withheld", all(inFile1.withheld == inFile2.withheld))
            sb_total += print_sb("key_point", all(inFile1.key_point == inFile2.key_point))


    ## Print summary
        print(str(passed) + " identical dimensions out of " + str(passed + failed))
        if not SUB_BYTE_COMPATABLE and PRESERVE:
            print("%i identical sub-byte fields out of %i" %(sb_total, 8))

        inFile1.close()
        inFile2.close()

def main():
    vf = lasverify()
    print("Verify Complete")
