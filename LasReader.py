import struct
import sys
import random



def binaryFmt(N, outArr):
    if N == 0:
        return(0)
    i = 0
    while 2**i <= N:
        i += 1
    i -= 1
    outArr.append(i)
    N -= 2**i
    if N == 0:
        return(outArr)
    return(binaryFmt(N, outArr))
    
def binaryStr(N):
    arr = binaryFmt(N, [])
    if arr == 0:
        return("0")
    outstr = ["0"]*(max(arr)+1)
    for i in arr:
        outstr[i] = "1"
    outstr.reverse() 
    outstr = "".join(outstr)
    return(outstr)
        
        
        


class PointDataRecord():
    def __init__(self, reader, version):
        self.Version = version
        self.X = reader.ReadWords("<L", 1, 4)
        self.Y = reader.ReadWords("<L", 1, 4)
        self.Z = reader.ReadWords("<L", 1, 4)
        self.Intensity = reader.ReadWords("<H", 1, 2)
        ## This next part might not be right - I think it needs to be 
        ## big endian to get this in the right order, but I don't know.
        ## Needs testing.
        BitPart = binaryStr(ord(reader.ReadWords(">s",1,1)))
        if len(BitPart) > 8:
            BitPart = "Z"*8
        BitPart = "0"*(8-len(BitPart))+BitPart
        self.ReturnNum = BitPart[0:3]
        self.NumReturns = BitPart[3:6]
        self.ScanDirFlag = BitPart[6]
        self.EdgeFlightFlag = BitPart[7]
        ###########################
        self.Classification = reader.ReadWords("<B", 1,1)
        self.ScanAngleRnk = reader.ReadWords("<c",1,1)
        self.UserData = reader.ReadWords("<B",1,1)
        self.PtSrcID = reader.ReadWords("<H",1,2)
        if self.Version in (1,3,4,5):
            self.GPSTime = reader.ReadWords("<d",1,8)
        if self.Version in (2,3,5):
            self.Red = reader.ReadWords("<H",1,2)
            self.Green = reader.ReadWords("<H",1,2)
            self.Blue = reader.ReadWords("<H",1,2)
        if self.Version in (4,5):
            self.WavePacketDescritproIdx = reader.ReadWords("<B",1,1)
            self.ByteOffsetToWaveFmData = reader.ReadWords("<Q",1,8)
            self.WaveFmPktSize = reader.ReadWords("<L",1,4)
            self.ReturnPtWavefmLoc = reader.ReadWords("<f",1,4)
            self.X_t = reader.ReadWords("<f",1,4)
            self.Y_t = reader.ReadWords("<f",1,4)
            self.Z_t = reader.ReadWords("<f",1,4)
    def summary(self):
        sys.stdout.write("\n### Point Record Information ###\n")
        sys.stdout.write("### X:         "+str(self.X)+"\n")       
        sys.stdout.write("### Y:         "+str(self.Y)+"\n")   
        sys.stdout.write("### Z:         "+str(self.Z)+"\n")       
        sys.stdout.write("### Intensity: "+str(self.Intensity)+"\n")       
        sys.stdout.write("\n")       

class ByteReader():
    def __init__(self, fileref):
        self.fileref = fileref
        self.Source = open(fileref, "rb")
        self.bytesRead = 0
        return

    def close(self):
        self.Source.close()
        return

    def read(self, bytes):
        self.bytesRead += bytes
        return(self.Source.read(bytes))
        
        
    def reset(self):
        self.Source.close()
        self.Source = open(self.fileref, "rb")
        return

    def ReadWords(self, fmt, num, bytes):
        outData = []
        for i in xrange(num):
            dat = self.read(bytes)
            outData.append(struct.unpack(fmt, dat)[0])
        if len(outData)>1:
            return(outData)
        return(outData[0])


class GeoKeyDirectoryTag():
    def __init__(self,reader):
        self.wKeyDirectoryVersion = reader.ReadWords("<H",1,2)
        self.wKeyRevision = reader.ReadWords("<H",1,2)
        self.wMinorRevision = reader.ReadWords("<H",1,2)
        self.wNumberOfKeys = reader.ReadWords("<H",1,2)
        self.Keys = []
        for i in xrange(self.wNumberOfKeys):
            #Tuples:  (wKeyID, wTIFFTagLocation, wCount, wValue_Offset)
            self.Keys.append(reader.ReadWords("<H",4,2))
        return        
        
class GeoAsciiParamsTag():
    def __init__(self,reader,recLen):
        outputStrings = []
        currentStr = ""
        for i in xrange(recLen):
            newChar = reader.ReadWords("<c",1,1)
            print(newChar)
            if newChar == "\0":
                outputStrings.append(currentStr)
                currentStr = ""
            else:
                currentStr += newChar
        if currentStr != "":
            outputStrings.append(currentStr)
        self.Data = outputStrings
        print(self.Data)
        return
        
        
        


class VarLenRec():
    def __init__(self,reader):
        self.Reserved = reader.ReadWords("<H", 1, 2)
        self.UserID = "".join(reader.ReadWords("<s", 16, 1))
        self.RecordID = reader.ReadWords("<H", 1, 2)
        self.RecLenAfterHeader = reader.ReadWords("<H",1,2)
        self.Description = "".join(reader.ReadWords("<s",32,1))
        ## Act on known VarLenRec Types
        if "GeoKeyDirectoryTag" in self.Description:

            self.Body = GeoKeyDirectoryTag(reader)
        elif "GeoAsciiParamsTag" in self.Description:
            # Does this need to use data from the GeoKeyDirectoryTag?
            self.Body = GeoAsciiParamsTag(reader, self.RecLenAfterHeader)
        elif "GeoAsciiDoubleParamsTag" in self.Description:
            self.VARLENRECDAT = reader.read(self.RecLenAfterHeader)
        elif "Classification" in self.Description:
            self.VARLENRECDAT = reader.read(self.RecLenAfterHeader)
        elif "Histogram" in self.Description:
            self.VARLENRECDAT = reader.read(self.RecLenAfterHeader) 
        elif "Text area description" in self.Description:
            self.VARLENRECDAT = reader.read(self.RecLenAfterHeader)
        else:
            sys.stdout.write("Unknown VarLenRec Type: " + self.Description+"\n")
            ### Temporary Cop out - just store the data in binary
            self.VARLENRECDAT = reader.read(self.RecLenAfterHeader)
        return

    def summary(self):
        sys.stdout.write("\n")
        sys.stdout.write("##########################################\n")
        sys.stdout.write("### Variable Length Record Information ###\n")
        sys.stdout.write("##########################################\n")
        sys.stdout.write("User ID:                       " + self.UserID+"\n")
        sys.stdout.write("Length of record after header: " +  str(self.RecLenAfterHeader)+"\n")
        sys.stdout.write("Description:                   " + self.Description+"\n")

class Header():
    def __init__(self, reader):
        self.FileSig = "".join(reader.ReadWords("<s", 4, 1))
        self.FileSrc = reader.ReadWords("<H",1,2)
        self.GlobalEncoding = reader.ReadWords("<H",1,2)
        self.ProjID1 = reader.ReadWords("<L",1,4)
        self.ProjID2 = reader.ReadWords("<H",1,2)
        self.ProjID3 = reader.ReadWords("<H",1,2)
        self.ProjID4 = "".join([str(x) for x in reader.ReadWords("<B",8,1)])
        self.VersionMajor = reader.ReadWords("<B",1,1)
        self.VersionMinor = reader.ReadWords("<B",1,1)
        self.Version = str(self.VersionMajor)+"."+str(self.VersionMinor)
        self.SysId = "".join(reader.ReadWords("<s",32,1))
        self.GenSoft = "".join(reader.ReadWords("<s",32,1))
        self.CreatedDay = reader.ReadWords("<H",1,2)
        self.CreatedYear = reader.ReadWords("<H",1,2)
        self.HeaderSize = reader.ReadWords("<H",1,2)
        self.OffsetToPointData = reader.ReadWords("<L",1,4)
        self.NumVariableLenRecs = reader.ReadWords("<L",1,4)
        self.PtDatFormatID = reader.ReadWords("<B",1,1)
        self.PtDatRecLen = reader.ReadWords("<H",1,2)
        self.NumPtRecs = reader.ReadWords("<L",1,4)

        if self.Version == "1.3":
            self.NumPtsByReturn = reader.ReadWords("<L",7,4)
        elif self.Version in ["1.0","1.1", "1.2"]:
            self.NumPtsByReturn = reader.ReadWords("<L",5,4)
        
        self.XScale = reader.ReadWords("<d",1,8)
        self.YScale = reader.ReadWords("<d",1,8)
        self.ZScale = reader.ReadWords("<d",1,8)
        self.XOffset = reader.ReadWords("<d",1,8)
        self.YOffset = reader.ReadWords("<d",1,8)
        self.ZOffset = reader.ReadWords("<d",1,8)
        self.XMax = reader.ReadWords("<d",1,8)
        self.XMin = reader.ReadWords("<d",1,8)
        self.YMax = reader.ReadWords("<d",1,8)
        self.YMin = reader.ReadWords("<d",1,8)
        self.ZMax = reader.ReadWords("<d",1,8)
        self.ZMin = reader.ReadWords("<d",1,8)
        if self.Version == "1.3":
            self.StWavefmDatPktRec = reader.ReadWords("<Q",1,8)

    def summary(self):
        sys.stdout.write("###############################"+"\n")
        sys.stdout.write("##### Summary Information #####"+"\n")
        sys.stdout.write("###############################\n")
        sys.stdout.write("### File Signiture:                    "+self.FileSig+"\n")
        sys.stdout.write("### LAS Version:                       "+ str(self.VersionMajor)+"."+str(self.VersionMinor)+"\n")
        sys.stdout.write("### Project ID Pt 1:                   "+ str(self.ProjID1)+"\n")
        sys.stdout.write("### Project ID Pt 2:                   "+ str(self.ProjID2)+"\n")
        sys.stdout.write("### Project ID Pt 3:                   "+ str(self.ProjID3)+"\n")
        sys.stdout.write("### Project ID pt 4:                   "+ self.ProjID4+"\n")
        sys.stdout.write("### Number of Variable Length Records: "+str(self.NumVariableLenRecs)+"\n")
        sys.stdout.write("### Number of Point Records:           "+str(self.NumPtRecs)+"\n")
        sys.stdout.write("### Size of header:                    "+ str(self.HeaderSize)+"\n")
        sys.stdout.write("\n")
        sys.stdout.write("###   Coordnate Stats: (Scale, Offset, Max, Min) "+"\n")
        sys.stdout.write("###             X: " + str((self.XScale, self.XOffset, self.XMax, self.XMin))+"\n")
        sys.stdout.write("###             Y: " + str((self.YScale, self.YOffset, self.YMax, self.YMin))+"\n")
        sys.stdout.write("###             Z: " + str((self.ZScale, self.ZOffset, self.ZMax, self.ZMin))+"\n")

class LasFileRec():
    def __init__(self, fileref):
        self.Reader = ByteReader(fileref)
        self.Header = Header(self.Reader)
        self.VariableLengthRecords = []
        for record in xrange(self.Header.NumVariableLenRecs):
            NewRec = VarLenRec(self.Reader)
            self.VariableLengthRecords.append(NewRec)
        if (self.Header.OffsetToPointData > self.Reader.bytesRead):
            sys.stdout.write("Warning: extra data encountered between last header and first record!\n") 
            self.ExtraData = self.Reader.read(self.Header.OffsetToPointData - self.Reader.bytesRead)
        elif (self.Header.OffsetToPointData < self.Reader.bytesRead):
            sys.stdout.write("Warning: last header extends past first record! Resetting reader...\n")
            self.Reader.reset()
            self.Reader.read(self.Header.OffsetToPointData)
        sys.stdout.write("Reading point data...\n")
        self.PointData = []
        if not (self.Header.PtDatFormatID in range(6)):
            sys.stdout.write("Error: Unrecognized Foramt Detected: "+ str(self.Header.PtDatFormatID)+"\n")
            sys.stdout.write("No points will be read, exiting.\n")
            return
        for ptRec in xrange(self.Header.NumPtRecs):
            self.PointData.append(PointDataRecord(self.Reader, self.Header.PtDatFormatID))
    def randomPtSummary(self,n):
        if len(self.PointData)==0:
            sys.stdout.write("There is no point data to sample.\n")
            return
            
        sys.stdout.write("\n Printing random selection of "+str(n)+" point record summaries. \n")
        for PR in xrange(n):
            # This doesn't guarantee unique random draws, but it really shouldn't matter.
            random.choice(self.PointData).summary()
            

                
            
            



if __name__ == "__main__":
    if (len(sys.argv)==2):
        LASFile = LasFileRec(sys.argv[1])
        LASFile.Header.summary()
        for VLR in LASFile.VariableLengthRecords:
            VLR.summary()

        LASFile.randomPtSummary(10)

        


#        except:
#            sys.stdout.write("Sorry, something broke.")
#        finally:
#            sys.stdout.write("End of Header")
#    else:
#        sys.stdout.write("Error: script requires one argument, referring to path of a LAS formatted file.")
