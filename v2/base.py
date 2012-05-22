#
# Provides base functions for manipulating files. 
import mmap
from header import Header, leap_year
import numpy as np
import sys
import struct


class Point():
    def __init__(self, bytestr,version, deepRead = False):
        self.Version = version
        self.X = self.ReadWords("<L", 1,bytestr, 4, 0)
        self.Y = self.ReadWords("<L", 1,bytestr, 4, 4)
        self.Z = self.ReadWords("<L", 1,bytestr, 4, 8)

            
    def ReadWords(self, fmt, num,dat,bytes, offs):
        outData = []
        idx = (0,4)
        for i in xrange(num):
            outData.append(struct.unpack(fmt,
                dat[idx[0]+bytes*i+offs:idx[1]+bytes*i+offs])[0])
        if len(outData > 1):
            return(outData)
        return(outData[0])


            



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

    def GetRawPoint(self, index):
        start = (self.Header.data_offset + index * self.Header.data_record_length)
        return(self._map[start : start + self.Header.data_record_length])

    def GetPoint(self, index):
        pass
    
    def GetNextPoint(self):
        pass

    def buildPointRefs(self):
        pts = self.get_pointrecordscount()
        print(pts)
        self.PointRefs = np.array(xrange(pts))
        print(self.PointRefs)
        self.PointRefs = self.GetRawPoint(self.PointRefs)
        print(self.PointRefs)
        return

    def GetX(self, scale=False):
        if self.PointRefs == False:
            self.buildPointRefs()
        
       

    def GetX(self, scale=False):
         if self.PointRefs == False:
            self.buildPointRefs()       

    def GetX(self, scale=False):
        if self.PointRefs == False:
            self.buildPointRefs()




class Writer():
    def __init__(self,filename):
        pass

    def close(self):
        pass

    def get_header(self):
        pass

    def set_header(self):
        pass


def CreateWithHeader(filename, header):
    pass
