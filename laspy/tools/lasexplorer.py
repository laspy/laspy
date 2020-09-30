import argparse
import laspy
import code

import logging
import sys

logger = logging.getLogger('lasexplorer')
ch = logging.StreamHandler(stream=sys.stderr)
fmrt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
formatter = logging.Formatter(fmrt)
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)


class lasexplorer():
    def __init__(self):
        self.parse_args()
        self.setup()

    def parse_args(self):
        parser = argparse.ArgumentParser(description="""Open a file in read mode and
                                        print a simple description.""")
        parser.add_argument("in_file", metavar="in_file",
                            type=str, nargs="+", help="LAS file to explore")
        parser.add_argument("--mode", metavar="file mode", type=str,
                            default="r",
                            help="Mode, default is r. Acceptable values: (r, rw)")  # noqa: E501
        parser.add_argument("-q", metavar="quiet", type=bool, default=False,
                            help="Skip summary? (default false)")

        self.args = parser.parse_args()

    def setup(self):
        # Check mode
        if self.args.mode == "rw":
            msg = f"Mode = {self.args.mode}, changes to file will be committed to disk."  # noqa: E501
            logger.debug(msg)
        elif self.args.mode != "r":
            logger.warning("Warning: invalud mode: " + self.args.mode)

        # Try to read in file
        logger.debug("Reading: " + self.args.in_file[0])
        try:
            inFile = laspy.file.File(self.args.in_file[0],
                                     mode=self.args.mode)
            self.inFile = inFile
            READ_SUCCESS = True
            logger.debug("Read successful, file object is called inFile")
        except Exception as error:
            logger.error(f"Error while reading file: {error}")
            READ_SUCCESS = False

    # If we have a file and user wants verbose, print summary.

        if READ_SUCCESS and not self.args.q:
            logger.debug("LAS File Summary:")
            logger.debug("File Version: " + str(inFile.header.version))
            logger.debug("Point Format: " + str(inFile.header.data_format_id))
            logger.debug("Number of Point Records: " + str(len(inFile)))
            logger.debug("Point Dimensions: ")
            for dim in inFile.point_format:
                logger.debug("    " + dim.name)

    def explore(self):
        inFile = self.inFile
        interp = code.InteractiveConsole(locals={"inFile": inFile})
        try:
            interp.interact()
        except (KeyboardInterrupt, SystemExit):
            quit()


def main():
    expl = lasexplorer()
    expl.explore()
