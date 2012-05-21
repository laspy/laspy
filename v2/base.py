#
# Provides base functions for manipulating files. 
import mmap
import Header
import numpy as np

class _reader():
    def __init__(self, filename):
        self.filename = filename
        self.fileref = open(filename, "rb")
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
        self._reader = _reader(filename)
        self.Header = False
        self.bytesRead = 0
        return        

    def GetHeader(self):
        if self.Header:
            return(self.Header)
        else:
            self.Header = Header(self._reader)
            
            
    
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





