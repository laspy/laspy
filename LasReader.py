import struct
import sys



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
        BitPart = binaryString(ord(reader.ReadWords(">s",1,1)))
        if len(BitPart) > 8:
            BitPart = "Z"*8
        BitPart = "0"*(8-len(BitPart))+BitPart
        self.ReturnNum = BitPart[0:3]
        self.NumReturns = BitPart[4:7]
        self.ScanDirFlag = BitPart[8]
        self.EdgeFlightFlag = BitPart[9]
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


class VarLenHeader():
    def __init__(self,reader):
        self.Reserved = reader.ReadWords("<H", 1, 2)
        self.UserID = "".join(reader.ReadWords("<s", 16, 1))
        self.RecordID = reader.ReadWords("<H", 1, 2)
        self.RecLenAfterHeader = reader.ReadWords("<H",1,2)
        self.Description = "".join(reader.ReadWords("<s",32,1))
        ## Act on known VarLenRec Types
        if "GeoKeyDirectoryTag" in self.Description:
            pass
        elif "GeoAsciiParamsTag" in self.Description:
            pass
        elif "GeoAsciiDoubleParamsTag" in self.Description:
            pass
        elif "Classification" in self.Description:
            pass
        elif "Histogram" in self.Description:
            pass
        elif "Text area description" in self.Description:
            pass

        ### Temporary Cop out - just store the data in binary
        self.VARLENRECDAT = reader.read(self.RecLenAfterHeader)
        return

    def summary(self):
        print("\n")
        print("##########################################")
        print("### Variable Length Record Information ###")
        print("##########################################\n")
        print("User ID:                       " + self.UserID)
        print("Length of record after header: " +  str(self.RecLenAfterHeader))
        print("Description:                   " + self.Description)

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
        print("###############################")
        print("##### Summary Information #####")
        print("###############################\n")
        print("### File Signiture:                    "+self.FileSig)
        print("### LAS Version:                       "+ str(self.VersionMajor)+"."+str(self.VersionMinor))
        print("### Project ID Pt 1:                   "+ str(self.ProjID1))
        print("### Project ID Pt 2:                   "+ str(self.ProjID2))
        print("### Project ID Pt 3:                   "+ str(self.ProjID3))
        print("### Project ID pt 4:                   "+ self.ProjID4)
        print("### Number of Variable Length Records: "+str(self.NumVariableLenRecs))
        print("### Size of header:                    "+ str(self.HeaderSize))
        print("\n")
        print("###   Coordnate Stats: (Scale, Offset, Max, Min) ")
        print("###             X: " + str((self.XScale, self.XOffset, self.XMax, self.XMin)))
        print("###             Y: " + str((self.YScale, self.YOffset, self.YMax, self.YMin)))
        print("###             Z: " + str((self.ZScale, self.ZOffset, self.ZMax, self.ZMin)))

class LasFileRec():
    def __init__(self, fileref):
        self.Reader = ByteReader(fileref)
        self.Header = Header(self.Reader)
        self.VariableLengthRecords = []
        for VarLenRec in xrange(self.Header.NumVariableLenRecs):
            NewHeader = VarLenHeader(self.Reader)
            self.VariableLengthRecords.append(NewHeader)
        if (self.Header.OffsetToPointData > self.Reader.bytesRead):
            print("Warning: extra data encountered between last header and first record!") 
            self.ExtraData = reader.read(self.Header.OffsetToPointData - self.Reader.BytesRead)
        elif (self.Header.OffsetToPointData < self.Reader.bytesRead):
            print("Warning: last header extends past first record! Resetting reader...")
            self.Reader.reset()
            self.Reader.read(self.Header.OffsetToPointData)
        print("Reading point data...")
            
            



if __name__ == "__main__":
    if (len(sys.argv)==2):
        LASFile = LasFileRec(sys.argv[1])
        LASFile.Header.summary()
        for VLR in LASFile.VariableLengthRecords:
            VLR.summary()


#        except:
#            print("Sorry, something broke.")
#        finally:
#            print("End of Header")
#    else:
#        print("Error: script requires one argument, referring to path of a LAS formatted file.")
