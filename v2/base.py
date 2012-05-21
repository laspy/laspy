#
# Provides base functions for manipulating files. 
import mmap
from header import Header, leap_year
import numpy as np
import sys
import struct


class _reader():
    def __init__(self, filename):
        self.filename = filename
        self.fileref = open(filename, "r+b")
        self._map = mmap.mmap(self.fileref.fileno(), 0)
        self.bytesRead = 0
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
    def ReadWords(self, fmt, num, bytes):
        outData = []
        for i in xrange(num):
            dat = self.read(bytes)
            outData.append(struct.unpack(fmt, dat)[0])
        if len(outData) > 1:
            return(outData)
        return(outData[0])

class Reader():
    def __init__(self,filename):
        self.Header = False
        self.VLRs = False
        self.bytesRead = 0
        self.filename = filename
        self.fileref = open(filename, "r+b")
        self._map = mmap.mmap(self.fileref.fileno(), 0)
        self.bytesRead = 0
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

    def GetVLRs(self):
        pass 
    
    def get_pointrecordscount(self):
        pass
       
    def SetInputSRS(self):
        pass
    
    def SetOutputSRS(self):
        pass

    def close(self):
        pass

    def GetPoint(self, index):
        pass
    
    def GetNextPoint(self):
        pass

    def Seek(self):
        pass

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
