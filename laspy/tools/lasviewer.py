import argparse
import laspy

class lasview():
    def __init__(self):
        self.parse_args()
        self.setup()

    def parse_args(self):
        parser =argparse.ArgumentParser(description = """Open a file in read mode and
                                        print a simple description.""")
        parser.add_argument("in_file", metavar = "in_file", 
                            type=str,nargs="+",help = "LAS file to plot")
        parser.add_argument("--mode",metavar="viewer_mode", type=str,default="default", 
                help = "Color Mode. Values to specify with a dimension: greyscale, heatmap.  Values which include a dimension: elevation, intensity, rgb")
        parser.add_argument("--dimension", metavar = "dim", type=str, default="intensity",
                help = "Color Dimension. Can be any single LAS dimension, default is intensity. Using color mode rgb, elevation, and intensity overrides this field.")

        self.args = parser.parse_args()
     
    def setup(self):
    # Check mode
        print("Reading: " + self.args.in_file[0])
        self.mode = self.args.mode
        self.dim = self.args.dimension
        try:
            inFile = laspy.file.File(self.args.in_file[0], mode = "r")
            self.inFile = inFile
        except Exception, error:
            print("Error while reading file:")
            print(error)
            quit()
        
    def view(self):
        self.inFile.visualize(self.mode, self.dim)

def main():
    expl = lasview()
    expl.view()


