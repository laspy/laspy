import argparse
import laspy
import numpy as np
import math

def main():
    parser =argparse.ArgumentParser(description = """Open a file in rw mode and add random noise to X Y and Z.""")
    parser.add_argument("in_file", metavar = "in_file", 
                        type=str,nargs="+",help = "LAS file to screw with.")
    parser.add_argument("--x_pct", metavar = "x_pct", type = float,default = 10, help = "Percent Of X Points to jiggle")
    parser.add_argument("--y_pct", metavar = "y_pct", type = float,default = 10, help = "Percent Of X Points to jiggle")
    parser.add_argument("--z_pct", metavar = "z_pct", type = float,default = 10, help = "Percent Of X Points to jiggle")
    parser.add_argument("--x_amt", metavar = "x_amt", type = int, default = 3, help = "Ammount to jiggle selected X points.") 
    parser.add_argument("--y_amt", metavar = "y_amt", type = int, default = 3, help = "Ammount to jiggle selected Y points.") 
    parser.add_argument("--z_amt", metavar = "z_amt", type = int, default = 3, help = "Ammount to jiggle selected Z points.") 


    args = parser.parse_args()



    inFile = laspy.file.File(args.in_file[0], mode = "rw")

    def gen_noise(pct, length, amt):
        out = np.zeros(length)
        indices = np.random.random_integers(0,length-1, math.floor(float(pct)/100*length))
        vals = np.random.random_integers(-amt,amt, len(indices))
        out[indices] += vals
        return(out)

    inFile.X += gen_noise(args.x_pct, len(inFile),args.x_amt)
    inFile.Y += gen_noise(args.y_pct, len(inFile),args.y_amt)
    inFile.Z += gen_noise(args.z_pct, len(inFile),args.z_amt)
    inFile.header.update_min_max()
    inFile.close(ignore_header_changes=True)



