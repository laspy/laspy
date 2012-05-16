import struct
import sys




        
class ByteReader():
    def __init__(self, fileref):
        self.fileref = fileref
        self.Source = open(fileref, "rb")
        return

    def close(self):
        self.Source.close()
        return

    def read(self, bytes):
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
            print("Version 1.3 Detected, grabbing StWavefmDatPktRec.")
            self.StWavefmDatPktRec = reader.ReadWords("<Q",1,8)

        self.VariableLengthRecords = []
        if self.NumVariableLenRecs == 0:
            print("Warning: zero variable length records requested - GeoKeyDirectoryTag is mandatory.")
            #self.VariableLengthRecords.append(VarLenHeader(reader))
            #self.VariableLengthRecords[0].summary()
        else:
            for i in range(self.NumVariableLenRecs):
                NewHeader = VarLenHeader(reader)
                self.VariableLengthRecords.append(NewHeader)
        return

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
        for VarLenRec in self.VariableLengthRecords:
            VarLenRec.summary()


if __name__ == "__main__":
    if (len(sys.argv)==2):
        Reader = ByteReader(sys.argv[1])
        Hdr = Header(Reader)
        Hdr.summary()
#        except:
#            print("Sorry, something broke.")
#        finally:
#            print("End of Header")
#    else:
#        print("Error: script requires one argument, referring to path of a LAS formatted file.")
