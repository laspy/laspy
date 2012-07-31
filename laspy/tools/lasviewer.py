import argparse
from laspy.file import File

class lasview():
    def __init__(self):
        self.parse_args()
        self.setup()

    def parse_args(self):
        parser =argparse.ArgumentParser(description = """Open a file in read mode and
                                        print a simple description.""")
        parser.add_argument("in_file", metavar = "in_file", 
                            type=str,nargs="+",help = "LAS file to explore")
        parser.add_argument("--mode",metavar="viewer_mode", type=str,default="intensity", 
                help = "Mode, default is intensity. Acceptable values are elevation, intensity, and, rgb.")



        self.args = parser.parse_args()
     
    def setup(self):
    # Check mode
        print("Reading: " + self.args.in_file[0])
        self.mode = self.args.mode
        try:
            inFile = File(self.args.in_file[0], mode = self.args.mode)
            self.inFile = inFile
        except Exception, error:
            print("Error while reading file:")
            print(error)
            quit()
        
    def view(self):
        self.inFile.visualize(self.mode)

def main():
    expl = lasview()
    expl.view()


