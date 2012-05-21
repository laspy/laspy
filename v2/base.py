### Provides base functions for manipulating files. 


class Reader():
    def __init__(self,filename):
        pass

    def GetHeader(self):
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





