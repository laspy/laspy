import laspy
import argparse

import sys
import logging

logger = logging.getLogger('lascopy')
ch = logging.StreamHandler(stream=sys.stderr)
fmrt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
formatter = logging.Formatter(fmrt)
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)


class lascopy():
    def __init__(self):
        self.parse_args()
        self.copy_data()

    def parse_args(self):
        '''Set up the argparser to accept command line arguments.'''
        parser = argparse.ArgumentParser(
            description="""Accept in_file and out_file .LAS files, and
                convert from in_file to out_file according to point_format
                and file_version.""")
        parser.add_argument('in_file', metavar='in_file', type=str,
                            nargs='+', help='input file path')
        parser.add_argument('out_file', metavar='out_file', type=str,
                            nargs='+', help='output file path')
        parser.add_argument('point_format', metavar='point_format', type=int,
                            nargs='+', help='output point format (0-10)')
        parser.add_argument('file_version', metavar='file_version', type=str,
                            nargs='+', help='output file version 1.0-1.4')
        parser.add_argument('-u', type=bool,
                            help="Update the header histogram? (slow)",
                            default=False)
        parser.add_argument('-b', type=bool,
                            help="Attempt to preserve incompatible sub-byte "
                            "sized data fields if present? (slow)",
                            default=False)

        self.args = parser.parse_args()

    def copy_data(self):
        """Set several global flags to determine lascopy behavior"""
        UPDATE_HISTOGRAM = self.args.u
        PRESERVE = self.args.b

        # Try to open in_file in read mode.
        file_version = self.args.file_version[0]
        point_format = self.args.point_format[0]
        try:
            inFile = laspy.file.File(self.args.in_file[0], mode="r")
        except Exception as error:
            print("There was an error reading in the input file: ")
            print(error)
            quit()

        # Verify that the user has supplied a compatible point_format
        # and file_version
        if not (point_format in range(11)):
            raise Exception("Invalid point format: %i" % point_format)
        if (point_format > 5 and file_version != "1.4"):
            raise Exception("Point formats 6-10 are only "
                            "supported by version 1.4 files.")
        if (point_format > 3 and not (file_version in ["1.3", "1.4"])):
            raise Exception("Point format %i is not "
                            "available for file version %s" %
                            (point_format, file_version))
        if (point_format >= 2 and not (file_version in ["1.2", "1.3", "1.4"])):
            raise Exception("Point format %i is not "
                            "available for file version %s" %
                            (point_format, file_version))

        # Store deprecated data for use later.
        old_file_version = inFile.header.version
        old_point_format = inFile.header.data_format_id

        # Set global flag, which indicates whether the input
        # and Output point formats have compatible sub-byte fields.
        SUB_BYTE_COMPATIBLE = (old_point_format <= 5) == (point_format <= 5)

        # Tell the user what we're doing.
        logger.debug("Input File: " + self.args.in_file[0] + ", %i point records." % len(inFile))
        logger.debug("Output File: " + self.args.out_file[0])
        logger.debug("Converting from file version %s to version %s."
                     % (old_file_version, file_version))
        logger.debug("Converting from point format %i to format %i."
                     % (old_point_format, point_format))

        # Warn the user if they chose potentially incompatible point
        # formats and didn't specify -b=True
        if (not SUB_BYTE_COMPATIBLE) and (not PRESERVE):
            warning = """ The sub-byte sized fields differ between point formats
                    %i and %i. By default this information will be lost. If you
                    want laspy to try to preserve as much as possible, specify
                    -b=True, though this may be quite slow depending on the
                    size of the dataset.""" % (old_point_format, point_format)
            logger.warning(warning)

        # Build the new header, check if we need to do anything
        # special. This includes:
        # 1. Check if there are extra dimensions defined which we need to copy.
        # 2. Check if we need to get rid of some/all EVLRs for the
        #    output file_version
        # 3. See if we need to re-map legacy fields for 1.4 files.
        try:
            new_header = inFile.header.copy()
            new_header.format = file_version
            new_header.data_format_id = point_format

            old_data_rec_len = new_header.data_record_length
            old_std_rec_len = laspy.util.Format(old_point_format).rec_len
            diff = old_data_rec_len - old_std_rec_len
            if (diff > 0):
                print("Extra Bytes Detected.")

            rl = laspy.util.Format(point_format).rec_len + ((diff > 0) * diff)
            logger.debug(f"Record length: {rl}")
            new_header.data_record_length = rl
            evlrs = inFile.header.evlrs
            if file_version != "1.4" and old_file_version == "1.4":
                msg = """input file has version 1.4, and output file does not.
                This may cause truncation of header data."""
                logger.warning(msg)
                retcount = inFile.header.legacy_point_return_count
                new_header.point_return_count = retcount
                reccount = inFile.header.legacy_point_records_count
                new_header.point_records_count = reccount

            if not (file_version in ["1.3", "1.4"]) and \
                    old_file_version in ["1.3", "1.4"]:
                logger.debug("Stripping any EVLRs")
                evlrs = []
            if (file_version == "1.3" and len(inFile.header.evlrs) > 1):
                message = "Too many EVLRs for format 1.3"
                logger.debug(message)
                evlrs = inFile.header.evlrs[0]

            outFile = laspy.file.File(self.args.out_file[0],
                                      header=new_header,
                                      mode="w",
                                      vlrs=inFile.header.vlrs,
                                      evlrs=evlrs)
            rl = outFile.point_format.rec_len
            if rl != outFile.header.data_record_length:
                pass
        except Exception as error:
            logger.error("There was an error instantiating the output file.")
            logger.error(error)
            quit()

        # Copy point dimensions.
        try:
            for dimension in inFile.point_format.specs:
                if dimension.name in outFile.point_format.lookup:
                    # Skip sub_byte field record bytes if incompatible
                    if (not SUB_BYTE_COMPATIBLE and dimension.name in
                            ("raw_classification",
                             "classification_flags",
                             "classification_byte",
                             "flag_byte")):
                        continue
                    dim = inFile.reader.get_dimension(dimension.name)
                    outFile.writer.set_dimension(dimension.name, dim)
                    logger.debug("Copying: " + dimension.name)

            # Do we need to do anything special for sub-byte fields?
            if (not SUB_BYTE_COMPATIBLE and PRESERVE):
                # Are we converting down or up?
                msg = "Copying sub-byte fields (this might take awhile)"
                logger.warning(msg)
                up = old_point_format < point_format
                if up:
                    outFile.classification = inFile.classification
                    outFile.return_num = inFile.return_num
                    outFile.num_returns = inFile.num_returns
                    outFile.scan_dir_flag = inFile.scan_dir_flag
                    outFile.edge_flight_line = inFile.edge_flight_line
                    outFile.synthetic = inFile.synthetic
                    outFile.withheld = inFile.withheld
                    outFile.key_point = inFile.key_point
                else:
                    try:
                        outFile.classification = inFile.classification
                    except Exception as error:
                        msg = f"Error, couldn't set classification. {error}"
                        logger.error(msg)
                    try:
                        outFile.return_num = inFile.return_num
                    except Exception as error:
                        msg = f"Error, couldn't set return number. {error}"
                        logger.error(msg)
                    try:
                        outFile.num_returns = inFile.num_returns
                    except AttributeError:
                        logger.error("Error, couldn't set number of returns.")
                    outFile.scan_dir_flag = inFile.scan_dir_flag
                    outFile.edge_flight_line = inFile.edge_flight_line
                    outFile.synthetic = inFile.synthetic
                    outFile.key_point = inFile.key_point
                    outFile.withheld = inFile.withheld

        except Exception as error:
            logger.error(f"Error copying data. {error}")
            quit()

        # Close the files, and optionally update new file histogram.
        inFile.close()
        outFile.close(ignore_header_changes=not UPDATE_HISTOGRAM)


def main():
    lascopy()
    logger.debug("Copy Complete")
