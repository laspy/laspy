#
# Provides base functions for manipulating files. 
import mmap
from header import Header, leap_year
import numpy as np
import sys
import struct

class Point():
    def __init__(self, reader, startIdx ,version):
        self.Version = version
        self.X = reader.ReadWords("<L", 1, 4)
        self.Y = reader.ReadWords("<L", 1, 4)
        self.Z = reader.ReadWords("<L", 1, 4)
        self.intensity = reader.ReadWords("<H", 1, 2)
        ###########################
        self.flag_byte = reader.ReadWords("<B",1,1)
        bstr = reader.binaryStr(self.flag_byte)
        self.return_num = reader.packedStr(bstr[0:3])
        self.num_returns = reader.packedStr(bstr[3:6])
        self.scan_dir_flag = reader.packedStr(bstr[6])
        self.edge_flight_line = reader.packedStr(bstr[7])
        ###########################
        self.raw_classification = reader.ReadWords("<B", 1,1)
        ##########################
        bstr = reader.binaryStr(self.raw_classification)
        self.classification = reader.packedStr(bstr[0:5])
        self.synthetic = reader.packedStr(bstr[5])
        self.key_point = reader.packedStr(bstr[6])
        self.withheld = reader.packedStr(bstr[7])       

        #########################

        self.scan_angle_rank = reader.ReadWords("<B",1,1)
        self.user_data = reader.ReadWords("<B",1,1)
        self.pt_src_id = reader.ReadWords("<H",1,2)
        if self.Version in (1,3,4,5):
            self.gps_time = reader.ReadWords("<d",1,8)
        if self.Version in (2,3,5):
            self.red = reader.ReadWords("<H",1,2)
            self.green = reader.ReadWords("<H",1,2)
            self.blue = reader.ReadWords("<H",1,2)
        if self.Version in (4,5):
            self.wave_packet_desc_index = reader.ReadWords("<B",1,1)
            self.byte_offset_to_waveform_data = reader.ReadWords("<Q",1,8)
            self.waveform_packet_size = reader.ReadWords("<L",1,4)
            self.return_pt_waveform_loc = reader.ReadWords("<f",1,4)
            self.x_t = reader.ReadWords("<f",1,4)
            self.y_t = reader.ReadWords("<f",1,4)
            self.z_t = reader.ReadWords("<f",1,4)

class VarLenRec():
    def __init__(self, reader):
        self.Reserved = reader.ReadWords("<H", 1, 2)
        self.UserID = "".join(reader.ReadWords("<s",16,1))
        self.RecordID = reader.ReadWords("<H", 1,2)
        self.RecLenAfterHeader = reader.ReadWords("<H",1,2)
        self.Description = "".join(reader.ReadWords("<s",32,1))

Formats={
"X":(0,"<L",4),
"Y":(4,"<L",4),
"Z":(8,"<L",4),
"Intensity":(12,"<H",2),
"FlagByte":(14,"<B",1),
"RawClassification":(15,"<B",1),
"ScanAngleRank":(16,"<B",1),
"UserData":(17,"<B",1),
"PtSrcId":(18,"<H",2),
"GPSTime":(20,"<d",8),
"Red_35":(28,"<H",2),
"Red_2":(20,"<H",2),
"Green_35":(30,"<H",2),
"Green_2":(22,"<H",2),
"Blue_35":(32,"<H",2),
"Blue_2":(24,"<H",2),
"WavePacketDescpIdx_5":(34,"<B",1),
"WavePacketDescpIdx_4":(28,"<B",1),
"ByteOffsetToWavefmData_5":(35,"<Q",8),
"ByteOffsetToWavefmData_4":(29,"<Q",8),
"WavefmPktSize_5":(43,"<L",4),
"WavefmPktSize_4":(37,"<L",4),
"ReturnPtWavefmLoc_5":(47,"<f",4),
"ReturnPtWavefmLoc_4":(41,"<f",4),
"X_t_5":(51,"<f",4),
"X_t_4":(45,"<f",4),
"Y_t_5":(56,"<f",4),
"Y_t_4":(49,"<f",4),
"Z_t_5":(60,"<f",4),
"Z_t_4":(54,"<f",4)}



class FileManager():
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
        self.PointRefs = False
        self._current = 0
        return
   
    def binaryFmt(self,N, outArr):
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
        return(self.binaryFmt(N, outArr))
    
    def packedStr(self, string, reverse = True):
        if reverse:
            string = "".join(reversed([x for x in string]))
            
        pwr = len(string)-1
        out = 0
        for item in string:
            out += int(item)*(2**pwr)
            pwr -= 1
        return(out)

    def binaryStr(self,N):
        arr = self.binaryFmt(N, [])
        if arr == 0:
            return("0"*8)
        outstr = ["0"]*(max(arr)+1)
        for i in arr:
            outstr[i] = "1"
        outstr = "".join(outstr)
        return(outstr + '0'*(8-len(outstr)))

    def read(self, bytes):
        self.bytesRead += bytes
        return(self._map.read(bytes))
    
    def reset(self):
        self._map.close()
        self.fileref.close()
        self.fileref = open(self.filename, "rb")
        self._map = mmap.mmap(self.fileref.fileno(), 0)
        return
     
    def seek(self, bytes, rel = True):
        # Seek relative to current pos
        self._current = None
        if rel:
            self._map.seek(bytes,1)
            return
        self._map.seek(bytes, 0)
        
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
            return((self._map.size()-
                self.Header.data_offset)/self.Header.data_record_length)
        return((self.Header.StWavefmDatPktRec-
                self.Header.data_offset)/self.Header.data_record_length)       
    def SetInputSRS(self):
        pass
    
    def SetOutputSRS(self):
        pass

    def GetRawPointIndex(self,index):
        return(self.Header.data_offset + 
            index*self.Header.data_record_length)

    def GetRawPoint(self, index):
        start = (self.Header.data_offset + 
            index * self.Header.data_record_length)
        return(self._map[start : start +
             self.Header.data_record_length])

#self, reader, startIdx ,version
    def GetPoint(self, index):
        if index >= self.get_pointrecordscount():
            return
        seekDex = self.GetRawPointIndex(index)
        self.seek(seekDex, rel = False)
        self._current = index
        return(Point(self, seekDex, self.Header.PtDatFormatID))
    
    def GetNextPoint(self):
        if self._current == None:
            raise Exception("No Current Point Specified," + 
                            " use Reader.GetPoint(0) first")
        return self.GetPoint(self._current + 1)

    def buildPointRefs(self):
        pts = self.get_pointrecordscount()
        self.PointRefs = np.array([self.GetRawPointIndex(i) 
                                     for i in xrange(pts)])
        return

    def GetDimension(self, name):
        try:
            specs = Formats[name]
            return(self._GetDimension(specs[0], specs[1], 
                                     specs[2]))
        except KeyError:
            raise Exception("Dimension: " + str(name) + 
                            "not found.")


    def _GetDimension(self,offs, fmt, length, raw = False):
        if type(self.PointRefs) == bool:
            self.buildPointRefs()
        if not raw:            
            return(map(lambda x: struct.unpack(fmt, 
                self._map[x+offs:x+offs+length])[0],self.PointRefs))
        return(map(lambda x: self._map[x+offs:x+offs+length]
            , self.PointRefs))
                
    def GetX(self, scale=False):
        return(self.GetDimension("X"))
       
    def GetY(self, scale=False):
        return(self.GetDimension("Y"))

    def GetZ(self, scale=False):
        return(self.GetDimension("Z"))
    
    def GetIntensity(self):
        return(self.GetDimension("Intensity"))
    
    def GetFlagByte(self):
        return(self.GetDimension("FlagByte"))
    
    def GetReturnNum(self):
        rawDim = self.GetFlagByte()
        return(map(lambda x: 
                    self.packedStr(self.binaryStr(x)[0:3]),
                    rawDim))

    def GetNumReturns(self):
        rawDim = self.GetFlagByte()
        return(map(lambda x: 
                    self.packedStr(self.binaryStr(x)[3:6]),
                    rawDim))

    def GetScanDirFlag(self):
        rawDim = self.GetFlagByte()
        return(map(lambda x:
                    self.packedStr(self.binaryStr(x)[6]),
                    rawDim))

    def GetEdgeFlightLine(self):
        rawDim = self.GetFlagByte()
        return(map(lambda x:
                    self.packedStr(self.binaryStr(x)[7]),
                    rawDim))

    def GetRawClassification(self):
        return(self.GetDimension("RawClassification"))
    
    def GetClassification(self):
        return(map(lambda x:
            self.packedStr(self.binaryStr(x)[0:5]),
            self.GetRawClassification()))

    def GetSynthetic(self):
        return(map(lambda x: int(self.binaryStr(x)[5]), 
                             self.GetRawClassification()))
    
    def GetKeyPoint(self):
        return(map(lambda x: int(self.binaryStr(x)[6]), 
                             self.GetRawClassification()))

    def GetWithheld(self):
        return(map(lambda x: int(self.binaryStr(x)[7]), 
                             self.GetRawClassification())) 

    def GetScanAngleRank(self):
        return(self.GetDimension("ScanAngleRank"))
    
    def GetUserData(self):
        return(self.GetDimension("UserData"))
    
    def GetPTSrcId(self):
        return(self.GetDimension("PtSrcId"))
    
    def GetGPSTime(self):
        fmt = self.Header.PtDatFormatID
        if fmt in (1,2,3,4,5):
            return(self.GetDimension("GPSTime"))
        raise Exception("GPS Time is not defined on pt format: "
                        + str(fmt))
    
    ColException = "Color is not available for point format: "
    def GetRed(self):
        fmt = self.Header.PtDatFormatID
        if fmt in (3,5):
            return(self.GetDimension("Red_35"))
        elif fmt == 2:
            return(self.GetDimension("Red_2"))
        raise Exception(ColException + str(fmt))
    
    def GetGreen(self):
        fmt = self.Header.PtDatFormatID
        if fmt in (3,5):
            return(self.GetDimension("Green_35"))
        elif fmt == 2:
            return(self.GetDimension("Green_2"))
        raise Exception(ColException + str(fmt))

    
    def GetBlue(self):
        fmt = self.Header.PtDatFormatID
        if fmt in (3,5):
            return(self.GetDimension("Blue_35"))
        elif fmt == 2:
            return(self.GetDimension("Blue_2"))
        raise Exception(ColException + str(fmt))


    def GetWavePacketDescpIdx(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension("WavePacketDescpIdx_5"))
        elif fmt == 4:
            return(self.GetDimension("WavePacketDescpIdx_4"))
        raise Exception("Wave Packet Description Index Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def GetByteOffsetToWavefmData(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension("ByteOffsetToWavefmData_5"))
        elif fmt == 4:
            return(self.GetDimension("ByteOffsetToWavefmData_4"))
        raise Exception("Byte Offset to Waveform Data Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def GetWavefmPktSize(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension("WavefmPktSize_5"))
        elif fmt == 4:
            return(self.GetDimension("WavefmPktSize_4"))
        raise Exception("Wave Packet Description Index Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def GetReturnPtWavefmLoc(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension("ReturnPtWavefmLoc_5"))
        elif fmt == 4:
            return(self.GetDimension("ReturnPtWavefmLoc_4"))
        raise Exception("ReturnPtWavefmLoc Not"
                       + " Available for Pt Fmt: " +str(fmt))



    def GetX_t(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension("X_t_5"))
        elif fmt == 4:
            return(self.GetDimension("X_t_4"))
        raise Exception("X(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

    def GetY_t(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension("Y_t_5"))
        elif fmt == 4:
            return(self.GetDimension("Y_t_4"))
        raise Exception("Y(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

    def GetZ_t(self):
        fmt = self.Header.PtDatFormatID
        if fmt == 5:
            return(self.GetDimension("Z_t_5"))
        elif fmt == 4:
            return(self.GetDimension("Z_t_4"))
        raise Exception("Z(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

class Reader(FileManager):
    def close(self):
        self._map.close()
        self.fileref.close()

class Writer(FileManager):

    def close(self):
        self._map.flush
        self._map.close()
        self.fileref.close()

    def SetHeader(self, header):
        pass    
    
    def set_padding(self, padding):
        pass
    
    def set_input_srs(self, srs):
        pass
    
    def set_output_srs(self, srs):
        pass

    def SetX(self,X, scale = False):
        pass

    def SetY(self,Y, scale = False):
        pass

    def SetZ(self, Z, scale = False):
        pass

    def SetIntensity(self, intensity):
        pass
    
    def SetFlagByte(self, byte):
        pass
    
    def SetReturnNum(self, num):
        pass

    def SetNumReturns(self, num):
        pass

    def SetScanDirFlag(self, flag):
        pass

    def SetEdgeFlightLine(self, line):
        pass

    def SetRawClassification(self, classification):
        pass
    
    def SetClassificaton(self, classification):
        pass

    def SetSynthetic(self, synthetic):
        pass

    def SetKeyPoint(self, pt):
        pass

    def SetWithheld(self, withheld):
        pass
    
    def SetScanAngleRank(self, rank):
        pass

    def SetUserData(self, data):
        pass
    
    def SetPtSrcId(self, data):
        pass
    
    def SetGPSTime(self, data):
        pass
    
    def SetRed(self, red):
        pass
    
    def SetGreen(self, green):
        pass
    
    def SetBlue(self, blue):
        pass
    
    def SetWavePacketDescpIdx(self, idx):
        pass
    
    def SetByteOffsetToWavefmData(self, idx):
        pass
    
    def SetWavefmPktSize(self, size):
        pass
    
    def SetReturnPtWavefmLoc(self, loc):
        pass
    
    def SetX_t(self, x):
        pass
    
    def SetY_t(self, y):
        pass
    
    def SetZ_t(self, z):
        pass
    
    


       




def CreateWithHeader(filename, header):
    pass
