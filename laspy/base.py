#
# Provides base functions for manipulating files. 
import mmap
from header import Header, leap_year
import numpy as np
import sys
import struct


class LaspyException(Exception):
    '''LaspyException: indicates a laspy related error.'''
    pass


fmtLen = {"<L":4, "<H":2, "<B":1, "<f":4, "<s":1, "<d":8, "<Q":8}
LEfmt = {"c_long":"<L", "c_ushort":"<H", "c_ubyte":"<B"
        ,"c_float":"<f", "c_char":"<s", "c_double":"<d", "c_ulonglong":"<Q"}

class Dimension():
    def __init__(self,name,offs, fmt, num,compress = False,ltl_endian = True):
        if ltl_endian:
            self.name = name
            self.offs = offs
            self.Format = fmt
            self.fmt = LEfmt[fmt]
            self.length = fmtLen[self.fmt]
            self.num = num
            self.compress = compress
        else:
            raise(LaspyException("Big endian files are not currently supported."))
    def __str__(self):
        return("Dimension Attributes \n" +
        "Name: " + self.name + "\n"+
        "Format: " + self.Format + "\n" +
        "Number: " + str(self.num) + "\n")
        


class Format():
    def __init__(self, fmt):
        fmt = str(fmt)
        self.dimensions = []
        if not (fmt in ("0", "1", "2", "3", "4", "5", "VLR", "h1.0", "h1.1", "h1.2", "h1.3")):
            raise LaspyException("Invalid format: " + str(fmt))
        ## Point Fields
        if fmt in ("0", "1", "2", "3", "4", "5"):
            self.add("X", 0, "c_long", 1)
            self.add("Y", 4, "c_long", 1)
            self.add("Z", 8, "c_long", 1)
            self.add("intensity", 12, "c_ushort", 1)
            self.add("flag_byte", 14,"c_ubyte", 1)
            self.add("raw_classification", 15,"c_ubyte", 1)
            self.add("scan_angle_rank",16, "c_ubyte", 1)
            self.add("user_data", 17, "c_ubyte", 1)
            self.add("pt_src_id", 18, "c_ushort", 1)
        if fmt in ("1", "3", "4", "5"):
            self.add("gps_time", 20, "c_double", 1)
        if fmt in ("3", "5"):
            self.add("red", 28, "c_ushort", 1)
            self.add("green", 30, "c_ushort", 1)
            self.add("blue" , 32, "c_ushort",1)
        elif fmt == "2":
            self.add("red", 20, "c_ushort", 1)
            self.add("green", 22, "c_ushort", 1)
            self.add("blue" , 24, "c_ushort",1)
        if fmt == "4":
            self.add("wave_packet_descp_idx", 28, "c_ubyte", 1)
            self.add("byte_offset_to_wavefm_data", 29, "c_ulonglong",1)
            self.add("wavefm_pkt_size", 37, "c_long", 1)
            self.add("return_pt_wavefm_loc", 41, "c_float", 1)
            self.add("X_t", 45, "c_float", 1)
            self.add("Y_t", 56, "c_float", 1)           
            self.add("Z_t", 54, "c_float", 1)
        elif fmt == "5":
            self.add("wave_packet_descp_idx", 34, "c_ubyte", 1)
            self.add("byte_offset_to_wavefm_data", 35, "c_ulonglong",1)
            self.add("wavefm_pkt_size", 43, "c_long", 1)
            self.add("return_pt_wavefm_loc", 47, "c_float", 1)
            self.add("X_t", 51, "c_float", 1)
            self.add("Y_t", 56, "c_float", 1)          
            self.add("Z_t", 60, "c_float", 1)
        ## VLR Fields
        if fmt == "VLR":
            self.add("Reserved", 0, "c_ushort", 1)
            self.add("UserID", 2, "c_char", 16)
            self.add("RecordID", 18, "c_ushort", 1)
            self.add("RecLenAfterHeader", 20, "c_ushort", 1)
            self.add("Descriptions", 22, "c_char", 32, compress = True)
        
        ## Header Fields
        if fmt[0] == "h":
            self.add("FileSig", 0, "c_char", 4, compress = True)
            self.add("FileSrc", 4, "c_ushort", 1)
            self.add("GlobalEncoding", 6, "c_ushort", 1)
            self.add("ProjID1", 8, "c_long", 1)
            self.add("ProjID2", 12, "c_ushort", 1)
            self.add("ProjID3", 14, "c_ushort", 1)
            self.add("ProjID4", 16, "c_ubyte", 8)
            self.add("VersionMajor", 24, "c_ubyte", 1)
            self.add("VersionMinor", 25, "c_ubyte", 1)
            self.add("SysId", 26, "c_char", 32, compress=True)
            self.add("GenSoft", 58, "c_char", 32, compress = True)
            self.add("CreatedDay", 90, "c_ushort", 1)
            self.add("CreatedYear", 92, "c_ushort",1)
            self.add("HeaderSize", 94, "c_ushort", 1)
            self.add("OffsetToPointData", 96, "c_long", 1)
            self.add("NumVariableLenRecs", 100, "c_long", 1)
            self.add("PtDatFormatID", 104, "c_ubyte", 1)
            self.add("PtDatRecLen", 105, "c_ushort", 1)
            self.add("NumPtRecs", 107, "c_long", 1)         
            if fmt == "h1.3":
                self.add("NumPtsByReturn", 108, "c_long", 7)
                self.add("XScale", 136, "c_double", 1)
                self.add("YScale", 144, "c_double", 1)
                self.add("ZScale", 152, "c_double", 1)
                self.add("XOffset", 160, "c_double", 1)
                self.add("YOffset", 168, "c_double", 1)
                self.add("ZOffset", 176, "c_double", 1) 
                self.add("XMax", 184, "c_double", 1)
                self.add("XMin", 192, "c_double", 1)
                self.add("YMax", 200, "c_double", 1)
                self.add("YMin", 208, "c_double", 1)
                self.add("ZMax", 216, "c_double", 1)
                self.add("ZMin", 224, "c_double", 1)
            elif fmt in ("h1.0", "h1.1", "h1.2"):
                self.add("NumPtsByReturn", 108, "c_long", 5)
                self.add("XScale", 128, "c_double", 1)
                self.add("YScale", 136, "c_double", 1)
                self.add("ZScale", 144, "c_double", 1)
                self.add("XOffset", 152, "c_double", 1)
                self.add("YOffset", 160, "c_double", 1)
                self.add("ZOffset", 168, "c_double", 1) 
                self.add("XMax", 176, "c_double", 1)
                self.add("XMin", 184, "c_double", 1)
                self.add("YMax", 192, "c_double", 1)
                self.add("YMin", 200, "c_double", 1)
                self.add("ZMax", 208, "c_double", 1)
                self.add("ZMin", 216, "c_double", 1)

        self.lookup = {}
        for dim in self.dimensions:
            self.lookup[dim.name] = [dim.offs, dim.fmt, dim.length, dim.compress]

    def add(self, name, offs, fmt, num, compress = False):
        self.dimensions.append(Dimension(name, offs, fmt, num, compress))
        
    def __str__(self):
        for dim in self.dimensions:
            dim.__str__()





class Point():
    def __init__(self, reader, startIdx):
        for dim in reader.point_format.dimensions:
            #reader.seek(dim.offs + startIdx, rel = False)
            self.__dict__[dim.name] = reader._ReadWords(dim.fmt, dim.num, dim.length)

        bstr = reader.binaryStr(self.flag_byte)
        self.return_num = reader.packedStr(bstr[0:3])
        self.num_returns = reader.packedStr(bstr[3:6])
        self.scan_dir_flag = reader.packedStr(bstr[6])
        self.edge_flight_line = reader.packedStr(bstr[7])

        bstr = reader.binaryStr(self.raw_classification)
        self.classification = reader.packedStr(bstr[0:5])
        self.synthetic = reader.packedStr(bstr[5])
        self.key_point = reader.packedStr(bstr[6])
        self.withheld = reader.packedStr(bstr[7])       

 


        
        


        
class VarLenRec():
    def __init__(self, reader):
        self.reserved = reader.ReadWords("Reserved")
        self.user_id = "".join(reader.ReadWords("UserID"))
        self.record_id = reader.ReadWords("RecordID")
        self.rec_len_after_header = reader.ReadWords("RecLenAfterHeader")
        self.description = "".join(reader.ReadWords("Description"))



class FileManager():
    def __init__(self,filename):
        self.header = False
        self.vlrs = False
        self.bytes_read = 0
        self.filename = filename
        self.fileref = open(filename, "r+b")
        self._map = mmap.mmap(self.fileref.fileno(), 0)
        self.header_format = Format("h" + self.grab_file_version())
        self.get_header()
        self.populateVLRs()
        self.PointRefs = False
        self._current = 0
        self.point_format = Format(self.header.PtDatFormatID)
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

    def binaryStr(self,N, zerolen = 8):
        arr = self.binaryFmt(N, [])
        if arr == 0:
            return("0"*zerolen)
        outstr = ["0"]*(max(arr)+1)
        for i in arr:
            outstr[i] = "1"
        outstr = "".join(outstr)
        padding = zerolen-len(outstr)
        if padding < 0:
            raise LaspyException("Invalid Data: Packed Length is Greater than allowed.")
        return(outstr + '0'*(zerolen-len(outstr)))

    def read(self, bytes):
        self.bytes_read += bytes
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
        
    def ReadWords(self, name):
        try:
            spec = Formats[name]
        except KeyError:
            raise LaspyException("Dimension " + name + "not found.")
        return(self._ReadWords(spec[1], spec[3], spec[2]))


    def _ReadWords(self, fmt, num, bytes):
        outData = []
        for i in xrange(num):
            dat = self.read(bytes)
            outData.append(struct.unpack(fmt, dat)[0])
        if len(outData) > 1:
            return(outData)
        return(outData[0])
    
    def grab_file_version(self):
        self.seek(24, rel = False)
        v1 = self._ReadWords("<B", 1, 1)
        v2 = self._ReadWords("<B", 1, 1)
        self.seek(0, rel = True)
        return(str(v1) +"." +  str(v2))

    def get_header(self):
        ## Why is this != neccesary?
        if self.header != False:
            return(self.header)
        else:
            self.header = Header(self)
    def populateVLRs(self):
        self.VLRs = []
        for i in xrange(self.header.NumVariableLenRecs):
            self.VLRs.append(VarLenRec(self))
            self.seek(self.VLRs[-1].RecLenAfterHeader)
            if self._map.tell() > self.header.data_offset:
                raise LaspyException("Error, Calculated Header Data "
                    "Overlaps The Point Records!")
        self.VLRStop = self._map.tell()
        return

    def GetVLRs(self):
        # This return needs to be modified
        return(self.VLRs)
    
    def get_padding(self):
        return(self.header.data_offset - self.VLRStop)

    def get_pointrecordscount(self):
        if self.header.get_version != "1.3":
            return((self._map.size()-
                self.header.data_offset)/self.header.data_record_length)
        return((self.header.StWavefmDatPktRec-
                self.header.data_offset)/self.header.data_record_length)       
    def SetInputSRS(self):
        pass
    
    def SetOutputSRS(self):
        pass

    def GetRawPointIndex(self,index):
        return(self.header.data_offset + 
            index*self.header.data_record_length)

    def GetRawPoint(self, index):
        start = (self.header.data_offset + 
            index * self.header.data_record_length)
        return(self._map[start : start +
             self.header.data_record_length])

#self, reader, startIdx ,version
    def GetPoint(self, index):
        if index >= self.get_pointrecordscount():
            return
        seekDex = self.GetRawPointIndex(index)
        self.seek(seekDex, rel = False)
        self._current = index
        return(Point(self, seekDex))
    
    def GetNextPoint(self):
        if self._current == None:
            raise LaspyException("No Current Point Specified," + 
                            " use Reader.GetPoint(0) first")
        return self.GetPoint(self._current + 1)

    def buildPointRefs(self):
        pts = self.get_pointrecordscount()
        self.PointRefs = np.array([self.GetRawPointIndex(i) 
                                     for i in xrange(pts)])
        return

    def GetDimension(self, name):
        try:
            specs = self.point_format.lookup[name]
            return(self._GetDimension(specs[0], specs[1], 
                                     specs[2]))
        except KeyError:
            raise LaspyException("Dimension: " + str(name) + 
                            "not found.")


    def _GetDimension(self,offs, fmt, length, raw = False):
        if type(self.PointRefs) == bool:
            self.buildPointRefs()
        if not raw:
            vfunc = np.vectorize(lambda x: struct.unpack(fmt, 
                self._map[x+offs:x+offs+length])[0])            
            return(vfunc(self.PointRefs))
        vfunc = np.vectorize(lambda x: 
            self._map[x+offs:x+offs+length])
        return(vfunc(self.PointRefs))
    

    ### To Implement: Scale            
    def GetX(self, scale=False):
        return(self.GetDimension("X"))
       
    def GetY(self, scale=False):
        return(self.GetDimension("Y"))

    def GetZ(self, scale=False):
        return(self.GetDimension("Z"))
    
    def GetIntensity(self):
        return(self.GetDimension("intensity"))
    
    def GetFlagByte(self):
        return(self.GetDimension("flag_byte"))
    
    def GetReturnNum(self):
        rawDim = self.GetFlagByte()
        vfunc = np.vectorize(lambda x: 
            self.packedStr(self.binaryStr(x)[0:3]))
        return(vfunc(rawDim))

    def GetNumReturns(self):
        rawDim = self.GetFlagByte()
        vfunc = np.vectorize(lambda x: 
            self.packedStr(self.binaryStr(x)[3:6]))
        return(vfunc(rawDim))

    def GetScanDirFlag(self):
        rawDim = self.GetFlagByte()
        vfunc = np.vectorize(lambda x: 
            self.packedStr(self.binaryStr(x)[6]))
        return(vfunc(rawDim))

    def GetEdgeFlightLine(self):
        rawDim = self.GetFlagByte()
        vfunc = np.vectorize(lambda x: 
            self.packedStr(self.binaryStr(x)[7]))
        return(vfunc(rawDim))

    def GetRawClassification(self):
        return(self.GetDimension("raw_classification"))
    
    def GetClassification(self): 
        vfunc = np.vectorize(lambda x: 
            self.packedStr(self.binaryStr(x)[0:5]))
        return(vfunc(self.GetRawClassification()))

    def GetSynthetic(self):
        vfunc = np.vectorize(lambda x: 
            self.packedStr(self.binaryStr(x)[5]))
        return(vfunc(self.GetRawClassification()))

    def GetKeyPoint(self):
        vfunc = np.vectorize(lambda x: 
            self.packedStr(self.binaryStr(x)[6]))
        return(vfunc(self.GetRawClassification()))

    def GetWithheld(self):
        vfunc = np.vectorize(lambda x: 
            self.packedStr(self.binaryStr(x)[7]))
        return(vfunc(self.GetRawClassification()))

    def GetScanAngleRank(self):
        return(self.GetDimension("scan_angle_rank"))
    
    def GetUserData(self):
        return(self.GetDimension("user_data"))
    
    def GetPTSrcId(self):
        return(self.GetDimension("pt_src_id"))
    
    def GetGPSTime(self):
        fmt = self.header.PtDatFormatID
        if fmt in (1,2,3,4,5):
            return(self.GetDimension("gps_time"))
        raise LaspyException("GPS Time is not defined on pt format: "
                        + str(fmt))
    
    ColException = "Color is not available for point format: "
    def GetRed(self):
        fmt = self.header.PtDatFormatID
        if fmt in (2,3,5):
            return(self.GetDimension("red"))
        raise LaspyException(ColException + str(fmt))
    
    def GetGreen(self):
        fmt = self.header.PtDatFormatID
        if fmt in (2,3,5):
            return(self.GetDimension("green"))
        raise LaspyException(ColException + str(fmt))

    
    def GetBlue(self):
        fmt = self.header.PtDatFormatID
        if fmt in (2,3,5):
            return(self.GetDimension("blue"))
        raise LaspyException(ColException + str(fmt))


    def GetWavePacketDescpIdx(self):
        fmt = self.header.PtDatFormatID
        if fmt in (4, 5):
            return(self.GetDimension("wave_packet_descp_idx"))
        raise LaspyException("Wave Packet Description Index Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def GetByteOffsetToWavefmData(self):
        fmt = self.header.PtDatFormatID
        if fmt in (4, 5):
            return(self.GetDimension("byte_offset_to_wavefm_data"))
        raise LaspyException("Byte Offset to Waveform Data Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def GetWavefmPktSize(self):
        fmt = self.header.PtDatFormatID
        if fmt in (4, 5):
            return(self.GetDimension("wavefm_pkt_size"))
        raise LaspyException("Wave Packet Description Index Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def GetReturnPtWavefmLoc(self):
        fmt = self.header.PtDatFormatID
        if fmt in (4, 5):
            return(self.GetDimension("return_pt_wavefm_loc"))
        raise LaspyException("Return Pointt Waveformm Loc Not"
                       + " Available for Pt Fmt: " +str(fmt))



    def GetX_t(self):
        fmt = self.header.PtDatFormatID
        if fmt in (4, 5):
            return(self.GetDimension("X_t"))
        raise LaspyException("X(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

    def GetY_t(self):
        fmt = self.header.PtDatFormatID
        if fmt in (4, 5):
            return(self.GetDimension("Y_t"))
        raise LaspyException("Y(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

    def GetZ_t(self):
        fmt = self.header.PtDatFormatID
        if fmt in (4, 5):
            return(self.GetDimension("Z_t"))
        raise LaspyException("Z(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

class Reader(FileManager):
    def close(self):
        self._map.close()
        self.fileref.close()

class Writer(FileManager):

    def close(self):
        self._map.flush()
        self._map.close()
        self.fileref.close()

    def SetDimension(self, name,dim):
        ptrecs = self.get_pointrecordscount()
        if len(dim) != ptrecs:
            raise LaspyException("Error, new dimension length (%s) does not match"%str(len(dim)) + " the number of points (%s)" % str(ptrecs))
        try:
            specs = self.point_format.lookup[name]
            return(self._SetDimension(dim,specs[0], specs[1], 
                                     specs[2]))
        except KeyError:
            raise LaspyException("Dimension: " + str(name) + 
                            "not found.")

    def _SetDimension(self,dim,offs, fmt, length):
        if type(self.PointRefs) == bool:
            self.buildPointRefs()
        idx = np.array(xrange(len(self.PointRefs)))
        def f(x):
            self._map[self.PointRefs[x]+offs:self.PointRefs[x]
                +offs+length] = struct.pack(fmt,dim[x])
        vfunc = np.vectorize(f)
        vfunc(idx)
        # Is this desireable
        #self._map.flush()
        return True


    def SetHeader(self, header):
        pass    
    
    def set_padding(self, padding):
        pass
    
    def set_input_srs(self, srs):
        pass
    
    def set_output_srs(self, srs):
        pass

    ##  To Implement: Scale
    def SetX(self,X, scale = False):
        self.SetDimension("X", X)
        return

    def SetY(self,Y, scale = False):
        self.SetDimension("Y", Y)
        return

    def SetZ(self, Z, scale = False):
        self.SetDimension("Z", Z)
        return

    def SetIntensity(self, intensity):
        self.SetDimension("intensity", intensity)
        return
    
    def SetFlagByte(self, byte):
        self.SetDimension("flag_byte", byte)
        return
    ##########
    # Utility Function, refactor
    
    def binaryStrArr(self, arr, length = 8):
        outArr = np.array(["0"*length]*len(arr))
        idx = 0
        for i in arr:
            outArr[idx] = self.binaryStr(i, length)
            idx += 1
        return(outArr)
        
    def compress(self,arrs,idx, pack = True):
        if pack:
            outArr = np.array([1]*len(arrs[0]))
        else:
            outArr = np.array(["0"*8]*len(arrs[0]))
       
        for i in xrange(len(arrs[0])):
            tmp = ""
            j = 0
            for arr in arrs:
                tmp += arr[i][idx[j][0]:idx[j][1]]
                j += 1
            if pack:
                tmp = self.packedStr(tmp)
            outArr[i] = tmp 
        
        return(outArr)


    ########


    def SetReturnNum(self, num):
        flagByte = self.binaryStrArr(self.GetFlagByte())
        newBits = self.binaryStrArr(num, 3)
        outByte = self.compress((newBits,flagByte), ((0,3), (3,8)))
        self.SetDimension("flag_byte", outByte)
        return

    def SetNumReturns(self, num):
        flagByte = self.binaryStrArr(self.GetFlagByte())
        newBits = self.binaryStrArr(num, 3)
        outByte = self.compress((flagByte,newBits,flagByte), 
            ((0,3),(0,3), (6,8)))
        self.SetDimension("flag_byte", outByte)
        return

    def SetScanDirFlag(self, flag): 
        flagByte = self.binaryStrArr(self.GetFlagByte())
        newBits = self.binaryStrArr(flag, 1)
        outByte = self.compress((flagByte,newBits,flagByte), 
            ((0,6),(0,1), (7,8)))
        self.SetDimension("flag_byte", outByte)
        return


    def SetEdgeFlightLine(self, line):
        flagByte = self.binaryStrArr(self.GetFlagByte())
        newBits = self.binaryStrArr(line, 1)
        outByte = self.compress((flagByte,newBits), 
            ((0,7),(0,1)))
        self.SetDimension("flag_byte", outByte)
        return

    def SetRawClassification(self, classification):
        self.SetDimension("raw_classification", classification)
    
    def SetClassificaton(self, classification):
        vfunc1 = np.vectorize(lambda x: self.binaryStr(x))
        vfunc2 = np.vectorize(lambda x: self.binaryStr(x, 5))
        vfunc3 = np.vectorize(lambda x: self.packedStr(newbits[x]
                          + classByte[x][5:8]))          
        classByte = vfunc1(self.GetRawClassification())
        newbits = vfunc2(classification)
        outByte = vfunc3(np.array(xrange(len(newBits))))
        self.SetDimension("flag_byte", outByte)
        return

    def SetSynthetic(self, synthetic):
        vfunc1 = np.vectorize(lambda x: self.binaryStr(x))
        vfunc2 = np.vectorize(lambda x: self.binaryStr(x, 1))
        vfunc3 = np.vectorize(lambda x: self.packedStr(
            classByte[x][0:5]
          + newbits[x]
          + classByte[x][6:8]))          
        classByte = vfunc1(self.GetRawClassification())
        newbits = vfunc2(synthetic)
        outByte = vfunc3(np.array(xrange(len(newBits))))
        self.SetDimension("flag_byte", outByte)
        return

    def SetKeyPoint(self, pt):
        vfunc1 = np.vectorize(lambda x: self.binaryStr(x))
        vfunc2 = np.vectorize(lambda x: self.binaryStr(x, 1))
        vfunc3 = np.vectorize(lambda x: self.packedStr(
            classByte[x][0:6]
          + newbits[x]
          + classByte[x][7]))          
        classByte = vfunc1(self.GetRawClassification())
        newbits = vfunc2(pt)
        outByte = vfunc3(np.array(xrange(len(newBits))))
        self.SetDimension("flag_byte", outByte)
        return
   
    def SetWithheld(self, withheld):
        vfunc1 = np.vectorize(lambda x: self.binaryStr(x))
        vfunc2 = np.vectorize(lambda x: self.binaryStr(x, 1))
        vfunc3 = np.vectorize(lambda x: self.packedStr(
            classByte[x][0:7]
          + newbits[x]))          
        classByte = vfunc1(self.GetRawClassification())
        newbits = vfunc2(withheld)
        outByte = vfunc3(np.array(xrange(len(newBits))))
        self.SetDimension("flag_byte", outByte)
        return

    def SetScanAngleRank(self, rank):
        self.SetDimension("scan_angle_rank", rank)
        return

    def SetUserData(self, data):
        self.SetDimension("user_data", data)
        return
    
    def SetPtSrcId(self, data):
        self.SetDimension("pt_src_id", data)
        return
    
    def SetGPSTime(self, data):
        vsn = self.header.PtDatFormatID
        if vsn in (1,2,3,4,5):    
            self.SetDimension("gps_time", data)
            return
        raise LaspyException("GPS Time is not available for point format: " + str(vsn))
    
    def SetRed(self, red):
        vsn = self.header.PtDatFormatID
        if vsn in (2,3,5):
            self.SetDimension("red", red)
            return
        raise LaspyException("Color Data Not Available for Point Format: " + str(vsn))

    def SetGreen(self, green):
        vsn = self.header.PtDatFormatID
        if vsn in (2,3,5):
            self.SetDimension("green", green)
            return
        raise LaspyException("Color Data Not Available for Point Format: " + str(vsn))


    
    def SetBlue(self, blue):
        vsn = self.header.PtDatFormatID
        if vsn in (2,3,5):
            self.SetDimension("blue", blue)
            return
        raise LaspyException("Color Data Not Available for Point Format: " + str(vsn))

    def SetWavePacketDescpIdx(self, idx):
        vsn = self.header.PtDatFormatID
        if vsn in (4, 5):
            self.SetDimension("wave_packet_descp_index", idx)
            return
        raise LaspyException("Waveform Packet Description Index Not Available for Point Format: " + str(vsn))

    def SetByteOffsetToWavefmData(self, idx):
        vsn = self.header.PtDatFormatID
        if vsn in (4, 5):
            self.SetDimension("byte_offset_to_wavefm_data", idx)
            return
        raise LaspyException("Byte Offset To Waveform Data Not Available for Point Format: " + str(vsn))


    
    def SetWavefmPktSize(self, size):
        vsn = self.header.PtDatFormatID
        if vsn in (4, 5):
            self.SetDimension("wavefm_pkt_size", size)
            return
        raise LaspyException("Waveform Packet Size Not Available for Point Format: " + str(vsn))
    
    def SetReturnPtWavefmLoc(self, loc):
        vsn = self.header.PtDatFormatID
        if vsn in (4, 5):
            self.SetDimension("return_pt_wavefm_loc", loc)
            return
        raise LaspyException("Return Point Waveform Loc Not Available for Point Format: " + str(vsn))


    
    def SetX_t(self, x):
        vsn = self.header.PtDatFormatID
        if vsn in (4, 5):
            self.SetDimension("X_t_5", x)
            return
        raise LaspyException("X_t Not Available for Point Format: " + str(vsn))

    def SetY_t(self, y):
        vsn = self.header.PtDatFormatID
        if vsn in (4, 5):
            self.SetDimension("Y_t", y)
            return
        raise LaspyException("Y_t Not Available for Point Format: " + str(vsn))
    
    def SetZ_t(self, z):
        vsn = self.header.PtDatFormatID
        if vsn in (4, 5):
            self.SetDimension("Z_t_5", z)
            return
        raise LaspyException("Z_t Not Available for Point Format: " + str(vsn))


    
    


       




def CreateWithHeader(filename, header):
    pass
