#
# Provides base functions for manipulating files. 
import mmap
from header import Header, leap_year
import numpy as np
import sys
import struct



class VarLenRec():
    def __init__(self, reader):
        self.Reserved = reader.ReadWords("<H", 1, 2)
        self.UserID = "".join(reader.ReadWords("<s",16,1))
        self.RecordID = reader.ReadWords("<H", 1,2)
        self.RecLenAfterHeader = reader.ReadWords("<H",1,2)
        self.Description = "".join(reader.ReadWords("<s",32,1))

class Reader():
    def __init__(self,filename):
        self.Header = False
        self.VLRs = False
        self.bytesRead = 0
        self.filename = filename
        self.fileref = open(filename, "r+b")
        self._map = mmap.mmap(self.fileref.fileno(), 0)
        self.bytesRead = 0
        self.GetHeader()
        self.populateVLRs()
        self.X = False
        self.Y = False
        self.Z = False
        self.PointRefs = False
        return
    
    def close(self):
        self._map.close()
        return

    def read(self, bytes):
        self.bytesRead += bytes
        return(self._map.read(bytes))
    
    def reset(self):
        self._map.close()
        self.fileref.close()
        self.fileref = open(self.filename, "rb")
        self._map = mmap.mmap(self.fileref.fileno(), 0)
        return
     
    def seek(self, bytes):
        # Seek relative to current pos
        self._map.seek(bytes,1)

    def ReadWords(self, fmt, num, bytes):
        outData = []
        for i in xrange(num):
            dat = self.read(bytes)
            outData.append(struct.unpack(fmt, dat)[0])
        if len(outData) > 1:
            return(outData)
        return(outData[0])


    def GetHeader(self):
        ## Why is this != neccesary?
        if self.Header != False:
            return(self.Header)
        else:
            self.Header = Header(self)
    
    def populateVLRs(self):
        self.VLRs = []
        for i in xrange(self.Header.NumVariableLenRecs):
            self.VLRs.append(VarLenRec(self))
            self.seek(self.VLRs[-1].RecLenAfterHeader)
            if self._map.tell() > self.Header.data_offset:
                raise Exception("Error, Calculated Header Data "
                    "Overlaps The Point Records!")
        self.VLRStop = self._map.tell()
        return

    def GetVLRs(self):
        # This return needs to be modified
        return(self.VLRs)
    
    def get_padding(self):
        return(self.Header.data_offset - self.VLRStop)

    def get_pointrecordscount(self):
        if self.Header.get_version != "1.3": 
            return((self._map.size()-self.Header.data_offset)/self.Header.data_record_length)
        return((self.Header.StWavefmDatPktRec - self.Header.data_offset)/self.Header.data_record_length)       

    def SetInputSRS(self):
        pass
    
    def SetOutputSRS(self):
        pass

    def close(self):
        pass

    def GetRawPointIndex(self,index):
        return(self.Header.data_offset + 
            index*self.Header.data_record_length)

    def GetRawPoint(self, index):
        start = (self.Header.data_offset + 
            index * self.Header.data_record_length)
        return(self._map[start : start +
             self.Header.data_record_length])

    def GetPoint(self, index):
        pass
    
    def GetNextPoint(self):
        pass

    def buildPointRefs(self):
        pts = self.get_pointrecordscount()
        self.PointRefs = np.array([self.GetRawPointIndex(i) for i in xrange(pts)])
        return

    def GetDimension(self,offs, fmt, length, raw = False):
        if type(self.PointRefs) == bool:
            self.buildPointRefs()
        if not raw:            
            return(map(lambda x: struct.unpack(fmt, 
                self._map[x+offs:x+offs+length]),self.PointRefs))
        return(map(lambda x: _map[x+ofs:x+ofs+length], self.PointRefs))
                

    def GetX(self, scale=False):
        return(self.GetDimension(0,"<L",4))
       
    def GetY(self, scale=False):
        return(self.GetDimension(4,"<L",4))

    def GetZ(self, scale=False):
        return(self.GetDimension(8,"<L",4))
    
    ## To Be Implemented
    
    def GetIntensity(self):
        return(self.GetDimension(12, "<H", 2))
    
    def GetFlagByte(self):
        return(self.GetDimension(14,"NA", 1, raw = True))
    
    def GetClassification(self):
        return(self.GetDimension(15, "<B",1))
    
    def GetScanAngleRank(self):
        return(self.GetDimension(16, "<c",1))
    
    def GetUserData(self):
        return(self.GetDimension(17, "<B", 1))
    
    def GetPTSrcId(self):
        return(self.GetDimension(18, "<H", 2))
    
    def GetGPSTime(self):
        fmt = self.Header.PtDatFormatID
        if fmt in (1,2,3,4,5):
            return(self.GetDimension(20, "<d", 8))
        raise Exception("GPS Time is not defined on pt format: "
                        + str(fmt))
    
    ColException = "Color is not available for point format: "
    def GetRed(self):
        fmt = self.Header.PtDatFormatID
        if fmt in (3,5):
            return(self.GetDimension(28, "<H", 2))
        elif fmt == 2:
            return(self.GetDimension(20, "<H",2))
        raise Exception(ColException + str(fmt))
    
    def GetGreen(self):
        fmt = self.Header.PtDatFormatID
        if fmt in (3,5):
            return(self.GetDimension(30, "<H", 2))
        elif fmt == 2:
            return(self.GetDimension(22, "<H",2))
        raise Exception(ColException + str(fmt))

    
    def GetBlue(self):
        fmt = self.Header.PtDatFormatID
        if fmt in (3,5):
            return(self.GetDimension(32, "<H", 2))
        elif fmt == 2:
            return(self.GetDimension(24, "<H",2))
        raise Exception(ColException + str(fmt))


    def GetWavePacketDescpIdx(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension(34, "<B", 1))
        elif fmt == 4:
            return(self.GetDimension(28, "<B", 1))
        raise Exception("Wave Packet Description Index Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def GetByteOffsetToWaveFmData(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension(35, "<Q", 8))
        elif fmt == 4:
            return(self.GetDimension(29, "<Q", 8))
        raise Exception("Byte Offset to Waveform Data Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def GetWavefmPktSize(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension(43, "<L", 4))
        elif fmt == 4:
            return(self.GetDimension(37, "<L", 4))
        raise Exception("Wave Packet Description Index Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def GetX_t(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension(47, "<f", 4))
        elif fmt == 4:
            return(self.GetDimension(41, "<f", 4))
        raise Exception("X(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

    def GetY_t(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension(51, "<f", 4))
        elif fmt == 4:
            return(self.GetDimension(45, "<f", 4))
        raise Exception("Y(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

    def GetZ_t(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension(56, "<f", 4))
        elif fmt == 4:
            return(self.GetDimension(49, "<f", 4))
        raise Exception("Z(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))





class Writer():
    def __init__(self,filename):
        pass

    def close(self):
        pass

    def get_header(self):
        pass
       




def CreateWithHeader(filename, header):
    pass
