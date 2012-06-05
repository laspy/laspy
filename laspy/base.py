#
# Provides base functions for manipulating files. 
import mmap
from header import Header, leap_year
import numpy as np
import struct
from util import *

class FileManager():
    def __init__(self,filename, mode, header = False, vlrs = False): 
        """Build the FileManager object. This is done when opening the file
        as well as upon completion of file modification actions like changing the 
        header padding."""
        self.vlrs = False
        self.header = header 
        self.filename = filename
        self.mode = mode
        if self.mode in ("r", "rw"):
                self.fileref = open(filename, "r+b")
                self._map = mmap.mmap(fileno = self.fileref.fileno(),length= 0)
                self.header_format = Format("h" + self.grab_file_version())
                self.vlr_formats = Format("VLR")
                self.get_header(mode)
                self.populate_vlrs()
                self.point_refs = False
                self.has_point_records = True
                self._current = 0
                self.point_format = Format(self.header.pt_dat_format_id) 
        elif self.mode == "w":
            if self.header == False:
                raise LaspyException("Write mode requires a valid header object.")
            self.fileref = open(filename, "w+b")
            self.header_format = self.header.format
            filesize = self.header_format.rec_len
            if vlrs != False:
                filesize += sum([len(x) for x in vlrs]) 
            if "pt_dat_format_id" in self.header.__dict__.keys():
                self.point_format = Format(self.header.__dict__["pt_dat_format_id"])
            else:
                self.point_format = Format("0") 
            #filesize += self.header.__dict__["point_records_count"]
            if "point_records_count" in self.header.__dict__.keys():
                self.has_point_records = True
                filesize += self.header.__dict__["point_records_count"]*self.point_format.rec_len
            else:
                self.has_point_records = False
            
            # Is there a faster way to do this?
            # Create Empty File
            self.fileref.write("\x00"*filesize)
            self.fileref.close()
            self.fileref= open(self.filename,"r+b")

            self._map = mmap.mmap(fileno = self.fileref.fileno(), length = 0)
            self.header.reader = self
            self.header.writer = self 
            self.header.version = str(self.header_format.fmt[1:])
            self.header.dump_data_to_file()  
             
            self.set_header_property("offset_to_point_data", max(self._map.size(), 
                                          self.header.data_offset)) 
            # This should be refactored
            if vlrs == False:
                vlrs = []
            self.set_header_property("num_variable_len_recs",len(vlrs))
            self.set_header_property("pt_dat_format_id", int(self.point_format.fmt))
            self.set_header_property("pt_dat_rec_len", int(self.point_format.rec_len))
            self.set_header_property("header_size", self.header_format.rec_len)
            self.header.refresh_attrs() 
            self.set_vlrs(vlrs)
            self.get_header(self.mode)
            self.populate_vlrs()
            self.seek(self.header.header_size, rel = False)
            self.point_refs = False
            self._current = 0

        elif self.mode == "w+":
            raise LaspyException("Append mode is not yet supported.")
        
        
        
        return
   
    def packed_str(self, string):
        """Take a little endian binary string, and convert it to a python int."""
        return(sum([int(string[idx])*(2**idx) for idx in xrange(len(string))]))

    def binary_str(self,N, zerolen = 8):
        """Take a python integer and create a binary string padded to len zerolen."""
        raw_bin = bin(N)[2:][::-1]
        padding = zerolen-len(raw_bin)
        if padding < 0:
            raise LaspyException("Invalid Data: Packed Length is Greater than allowed.")
        return(raw_bin + '0'*(zerolen-len(raw_bin)))

    def read(self, bytes):
        """Wrapper for mmap.mmap read function"""
        return(self._map.read(bytes))
    
    def reset(self):
        """Refresh the mmap and fileref"""
        self._map.close()
        self.fileref.close()
        self.fileref = open(self.filename, "rb")
        self._map = mmap.mmap(self.fileref.fileno(), 0)
        return
     
    def seek(self, bytes, rel = True):
        """Wrapper for mmap.mmap seek functions, make option rel explicit"""
        self._current = None
        if rel:
            self._map.seek(bytes,1)
            return
        self._map.seek(bytes, 0)
        
    def read_words(self, name):
        try:
            dim = self.vlr_formats.lookup[name]
        except KeyError:
            raise LaspyException("Dimension " + name + " not found.")
        return(self._read_words(dim.fmt, dim.num, dim.length))


    def _read_words(self, fmt, num, bytes):
        """Read a consecutive sequence of packed binary data, return a single
        element or list"""
        outData = []
        for i in xrange(num):
            dat = self.read(bytes)
            outData.append(struct.unpack(fmt, dat)[0])
        if len(outData) > 1:
            return(outData)
        return(outData[0])
    
    def grab_file_version(self):
        """Manually grab file version from header"""
        self.seek(24, rel = False)
        v1 = self._read_words("<B", 1, 1)
        v2 = self._read_words("<B", 1, 1)
        self.seek(0, rel = True)
        return(str(v1) +"." +  str(v2))

    def get_header(self, mode):
        """Return the header object. Depricated?"""
        ## Why is this != neccesary?
        if self.header != False:
            if self.header.file_mode != mode:
                raise LaspyException("Header Mode Conflict")
            return(self.header)
        else:
            self.header = Header(self, mode)

    def populate_vlrs(self):
        """Catalogue the variable length records"""
        self.vlrs = []
        self.seek(self.header.header_size, rel = False)
        for i in xrange(self.header.num_variable_len_recs): 
            self.vlrs.append(var_len_rec(self))
            #self.seek(self.vlrs[-1].rec_len_after_header)
            if self._map.tell() > self.header.data_offset:
                self.seek(self.header.data_offset, rel = False)
                raise LaspyException("Error, Calculated Header Data "
                    "Overlaps The Point Records!")
        self.vlr_stop = self._map.tell()
        return

    def get_vlrs(self):
        self.populate_vlrs()
        return(self.vlrs)
    
    def get_padding(self):
        """Return the padding between the end of the VLRs and the beginning of
        the point records"""
        return(self.header.data_offset - self.vlr_stop)

    def get_pointrecordscount(self):
        """calculate the number of point records"""
        if self.header.get_version != "1.3":
            return((self._map.size()-
                self.header.data_offset)/self.header.data_record_length)
        return((self.header.StWavefmDatPktRec-
                self.header.data_offset)/self.header.data_record_length)       
    def set_input_srs(self):
        pass
    
    def set_output_srsS(self):
        pass

    def get_raw_point_index(self,index):
        """Return the byte index of point number index"""
        return(self.header.data_offset + 
            index*self.header.data_record_length)

    def get_raw_point(self, index):
        """Return the raw bytestring associated with point of number index"""
        start = (self.header.data_offset + 
            index * self.header.data_record_length)
        return(self._map[start : start +
             self.header.data_record_length])

#self, reader, startIdx ,version
    def get_point(self, index):
        """Return point object for point of number index / #legacy_api""" 
        if index >= self.get_pointrecordscount():
            return
        seekDex = self.get_raw_point_index(index)
        self.seek(seekDex, rel = False)
        self._current = index
        return(Point(self, seekDex))
    
    def get_next_point(self):
        """Return next point object via get_point / #legacy_api"""
        if self._current == None:
            raise LaspyException("No Current Point Specified," + 
                            " use Reader.GetPoint(0) first")
        if self._current == self.get_pointrecordscount():
            return
        return self.get_point(self._current + 1)

    def build_point_refs(self):
        """Build array of point offsets """
        pts = self.get_pointrecordscount()
        self.point_refs = np.array([self.get_raw_point_index(i) 
                                     for i in xrange(pts)])
        return

    def get_dimension(self, name):
        """Return point dimension of with above name, returns numpy array"""
        try:
            spec = self.point_format.lookup[name]
            return(self._get_dimension(spec.offs, spec.fmt, 
                                     spec.length))
        except KeyError:
            raise LaspyException("Dimension: " + str(name) + 
                            "not found.")
    def _get_dimension(self,offs, fmt, length, raw = False):
        """Return point dimension of specified offset format and length"""
        if type(self.point_refs) == bool:
            self.build_point_refs()
        if not raw:
            vfunc = np.vectorize(lambda x: struct.unpack(fmt, 
                self._map[x+offs:x+offs+length])[0])            
            return(vfunc(self.point_refs))
        vfunc = np.vectorize(lambda x: 
            self._map[x+offs:x+offs+length])
        return(vfunc(self.PointRefs))
    

    def _get_raw_datum(self, rec_offs, spec):
        """return raw bytes associated with non dimension field (VLR/Header)"""
        return(self._map[(rec_offs + spec.offs):(rec_offs + spec.offs 
                        + spec.num*spec.length)])

    def _get_datum(self, rec_offs, spec):
        """Return unpacked data assocaited with non dimension field (VLR/Header)"""
        data = self._get_raw_datum(rec_offs, spec)
        if spec.num == 1:
            return(struct.unpack(spec.fmt, data)[0])
        unpacked = map(lambda x: struct.unpack(spec.fmt, 
            data[x*spec.length:(x+1)*spec.length])[0], xrange(spec.num))
        if spec.pack:
            return("".join([str(x[0]) for x in unpacked]))
        return(unpacked) 

    def get_raw_header_property(self, name):
        """Wrapper for grabbing raw header bytes with _get_raw_datum"""
        spec = self.header_format.lookup[name]
        return(self._get_raw_datum(0, spec))
    
    def get_header_property(self, name):
        """Wrapper for grabbing unpacked header data with _get_datum"""
        spec = self.header_format.lookup[name]
        return(self._get_datum(0, spec))

    ### To Implement: Scale            
    def get_x(self, scale=False):
        return(self.get_dimension("X"))
       
    def get_y(self, scale=False):
        return(self.get_dimension("Y"))

    def get_z(self, scale=False):
        return(self.get_dimension("Z"))
    
    def get_intensity(self):
        return(self.get_dimension("intensity"))
    
    def get_flag_byte(self):
        return(self.get_dimension("flag_byte"))
    
    def get_return_num(self):
        rawDim = self.get_flag_byte()
        vfunc = np.vectorize(lambda x: 
            self.packed_str(self.binary_str(x)[0:3]))
        return(vfunc(rawDim))

    def get_num_returns(self):
        rawDim = self.get_flag_byte()
        vfunc = np.vectorize(lambda x: 
            self.packed_str(self.binary_str(x)[3:6]))
        return(vfunc(rawDim))

    def get_scan_dir_flag(self):
        rawDim = self.get_flag_byte()
        vfunc = np.vectorize(lambda x: 
            self.packed_str(self.binary_str(x)[6]))
        return(vfunc(rawDim))

    def get_edge_flight_line(self):
        rawDim = self.get_flag_byte()
        vfunc = np.vectorize(lambda x: 
            self.packed_str(self.binary_str(x)[7]))
        return(vfunc(rawDim))

    def get_raw_classification(self):
        return(self.get_dimension("raw_classification"))
    
    def get_classification(self): 
        vfunc = np.vectorize(lambda x: 
            self.packed_str(self.binary_str(x)[0:5]))
        return(vfunc(self.get_raw_classification()))

    def get_synthetic(self):
        vfunc = np.vectorize(lambda x: 
            self.packed_str(self.binary_str(x)[5]))
        return(vfunc(self.get_raw_classification()))

    def get_key_point(self):
        vfunc = np.vectorize(lambda x: 
            self.packed_str(self.binary_str(x)[6]))
        return(vfunc(self.get_raw_classification()))

    def get_withheld(self):
        vfunc = np.vectorize(lambda x: 
            self.packed_str(self.binary_str(x)[7]))
        return(vfunc(self.get_raw_classification()))

    def get_scan_angle_rank(self):
        return(self.get_dimension("scan_angle_rank"))
    
    def get_user_data(self):
        return(self.get_dimension("user_data"))
    
    def get_pt_src_id(self):
        return(self.get_dimension("pt_src_id"))
    
    def get_gps_time(self):
        fmt = self.header.pt_dat_format_id
        if fmt in (1,2,3,4,5):
            return(self.get_dimension("gps_time"))
        raise LaspyException("GPS Time is not defined on pt format: "
                        + str(fmt))
    
    ColException = "Color is not available for point format: "
    def get_red(self):
        fmt = self.header.pt_dat_format_id
        if fmt in (2,3,5):
            return(self.get_dimension("red"))
        raise LaspyException(ColException + str(fmt))
    
    def get_green(self):
        fmt = self.header.pt_dat_format_id
        if fmt in (2,3,5):
            return(self.get_dimension("green"))
        raise LaspyException(ColException + str(fmt))

    
    def get_blue(self):
        fmt = self.header.pt_dat_format_id
        if fmt in (2,3,5):
            return(self.get_dimension("blue"))
        raise LaspyException(ColException + str(fmt))


    def get_wave_packet_descp_idx(self):
        fmt = self.header.pt_dat_format_id
        if fmt in (4, 5):
            return(self.get_dimension("wave_packet_descp_idx"))
        raise LaspyException("Wave Packet Description Index Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def get_byte_offset_to_wavefm_data(self):
        fmt = self.header.pt_dat_format_id
        if fmt in (4, 5):
            return(self.get_dimension("byte_offset_to_wavefm_data"))
        raise LaspyException("Byte Offset to Waveform Data Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def get_wavefm_pkt_size(self):
        fmt = self.header.pt_dat_format_id
        if fmt in (4, 5):
            return(self.get_dimension("wavefm_pkt_size"))
        raise LaspyException("Wave Packet Description Index Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def get_return_pt_wavefm_loc(self):
        fmt = self.header.pt_dat_format_id
        if fmt in (4, 5):
            return(self.get_dimension("return_pt_wavefm_loc"))
        raise LaspyException("Return Pointt Waveformm Loc Not"
                       + " Available for Pt Fmt: " +str(fmt))

    def get_x_t(self):
        fmt = self.header.pt_dat_format_id
        if fmt in (4, 5):
            return(self.get_dimension("X_t"))
        raise LaspyException("X(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

    def get_y_t(self):
        fmt = self.header.pt_dat_format_id
        if fmt in (4, 5):
            return(self.get_dimension("Y_t"))
        raise LaspyException("Y(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

    def get_z_t(self):
        fmt = self.header.pt_dat_format_id
        if fmt in (4, 5):
            return(self.get_dimension("Z_t"))
        raise LaspyException("Z(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

class Reader(FileManager):
    def close(self):
        self._map.close()
        self.fileref.close()

class Writer(FileManager):

    def close(self, ignore_header_changes = False):
        """Flush changes to mmap and close mmap and fileref"""
        if not ignore_header_changes:
            self.header.update_histogram()
            self.header.update_min_max() 
        self._map.flush()
        self._map.close()
        self.fileref.close()
    
    def set_vlrs(self, value):
        if value == False or len(value) == 0:
            return
        if not all([x.isVLR for x in value]):
            raise LaspyException("set_vlrs requers an iterable object " + 
                                 "composed of laspy.base.var_len_rec objects.")
        elif self.mode == "w+":
            raise NotImplementedError
        elif self.mode in ("w", "rw"): 
            current_padding = self.get_padding()
            old_offset = self.header.data_offset
            self.seek(0, rel = False)
            dat_part_1 = self._map.read(self.header.header_size)
            self.seek(old_offset, rel = False)
            dat_part_2 = self._map.read(len(self._map) - old_offset)
            self._map.close()
            self.fileref.close()
            self.fileref = open(self.filename, "w+b")
            self.fileref.write(dat_part_1)
            for vlr in value:
                self.fileref.write(vlr.to_byte_string())
            ## Is there a faster way to do this?
            self.fileref.write("\x00"*current_padding)
            self.fileref.write(dat_part_2)
            self.fileref.close()
            self.fileref = open(self.filename, "r+b")
            self._map = mmap.mmap(self.fileref.fileno(), 0)
        else:
            raise(LaspyException("set_vlrs requires the file to be opened in a write mode. "))

    def set_padding(self, value):
        """Set the padding between end of VLRs and beginning of point data"""
        if value < 0: 
            raise LaspyException("New Padding Value Overwrites VLRs")
        if self.mode == "w":
            raise NotImplementedError
        elif self.mode == "rw":
            old_offset = self.header.data_offset
            self.set_header_property("offset_to_point_data",
                                            self.vlr_stop +  value)
            #self.header.data_offset = self.vlr_stop + value 
            self._map.flush() 
            self.seek(0, rel=False)
            dat_part_1 = self._map.read(self.vlr_stop)
            self.seek(old_offset, rel = False)
            dat_part_2 = self._map.read(len(self._map) - old_offset)
            self._map.close()
            self.fileref.close()
            self.fileref = open(self.filename, "w+b")
            self.fileref.write(dat_part_1) 
            self.fileref.write("\x00"*value)
            self.fileref.write(dat_part_2)
            self.fileref.close()
            self.__init__(self.filename, self.mode)            
           
         
            return(len(self._map))
        elif self.mode == "r+":
            pass
        else:
            raise(LaspyException("Must be in write mode to change padding."))
        return(len(self._map))
    
    def pad_file_for_point_recs(self,num_recs):
        bytes_to_pad = num_recs * self.point_format.rec_len
        old_size = len(self._map)
        self._map.flush()
        self.fileref.seek(old_size, 0)
        self.fileref.write("\x00" * (bytes_to_pad + self.get_padding() ))
        self.fileref.flush()
        try:
            self._map.resize(old_size + bytes_to_pad)
        except(SystemError):
            #Older Python doesn't support resize
            self._map.close()
            self._map = mmap.mmap(self.fileref.fileno(), 0)
            self._map.flush()
        return

    def set_dimension(self, name,new_dim):
        if not self.has_point_records:
            self.has_point_records = True
            self.pad_file_for_point_recs(len(new_dim))
        """Set a point dimension of appropriate name to new_dim"""
        ptrecs = self.get_pointrecordscount()
        if len(new_dim) != ptrecs:
            raise LaspyException("Error, new dimension length (%s) does not match"%str(len(new_dim)) + " the number of points (%s)" % str(ptrecs))
        try:
            spec = self.point_format.lookup[name]
            return(self._set_dimension(new_dim,spec.offs, spec.fmt, 
                                     spec.length))
        except KeyError:
            raise LaspyException("Dimension: " + str(name) + 
                            "not found.")
 
    def _set_dimension(self,new_dim,offs, fmt, length):
        """Set a point dimension of appropriate offset format and length to new_dim"""
        if type(self.point_refs) == bool:
            self.build_point_refs()
        idx = np.array(xrange(len(self.point_refs)))
        def f(x):
            self._map[self.point_refs[x]+offs:self.point_refs[x]
                +offs+length] = struct.pack(fmt,new_dim[x])
        vfunc = np.vectorize(f)
        vfunc(idx)
        # Is this desireable
        #self._map.flush()
        return True

    def _set_raw_datum(self, rec_offs, spec, val):
        """Set a non dimension field with appropriate record type offset (0 for header)
        , appropriate spec object, and a new value. Uses raw bytes."""
        self._map[rec_offs+spec.offs:rec_offs+spec.offs +
                  spec.num*spec.length] = val
        return
    
    def _set_datum(self, rec_offs, dim, val):
        """Set a non dimension field as with _set_raw_datum, but supply a formatted value"""
     
        if dim.num == 1:
            lb = rec_offs + dim.offs
            ub = lb + dim.length 
            self._map[lb:ub] = struct.pack(dim.fmt, val)
            return

        try:
            dimlen = len(val)
        except(Exception):
            dimlen = 1

        if dim.num != dimlen:
            raise(LaspyException("Fields must be replaced with data of the same length. " + 
                                str(dim.name) +" should be length " + 
                                str(dim.num) +", received " + str(dimlen) ))


        def f(x):
            self._map[(x*dim.length + rec_offs + 
                    dim.offs):((x+1)*dim.length + rec_offs 
                    + dim.offs)]=struct.pack(dim.fmt, val[x])
        map(f, xrange(dim.num))
        return

    def set_raw_header_property(self, name, value):
        """Wrapper for _set_raw_datum, accpeting name of header property and raw byte value. """
        try:
            spec = self.header_format.lookup[name]
        except(KeyError):
            raise(LaspyException("Header Dimension: " + 
                  str(name) + " not found."))
        self._set_raw_datum(0, spec, value)

    def set_header_property(self, name, value):
        """Wrapper for _set_datum, accepting name of header property and formatted value"""
        try:
            dim = self.header_format.lookup[name]
        except(KeyError):
            raise LaspyException("Header Dimension: " + str(name) + " not found.")
        if not dim.overwritable:
            raise(LaspyException("Field " + dim.name + " is not overwritable."))
        
        self._set_datum(0, dim, value)
        return

    def set_header(self, header):
        pass     
    
    def set_input_srs(self, srs):
        pass
    
    def set_output_srs(self, srs):
        pass

    ##  To Implement: Scale
    def set_x(self,X, scale = False):
        self.set_dimension("X", X)
        return

    def set_y(self,Y, scale = False):
        self.set_dimension("Y", Y)
        return

    def set_z(self, Z, scale = False):
        self.set_dimension("Z", Z)
        return

    def set_intensity(self, intensity):
        self.set_dimension("intensity", intensity)
        return
    
    def set_flag_byte(self, byte):
        self.set_dimension("flag_byte", byte)
        return
    
    ##########
    # Utility Functions, refactor
    
    def binary_str_arr(self, arr, length = 8):
        return(np.array([self.binary_str(x, length) for x in arr]))

    def bitpack(self,arrs,idx, pack = True):
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
                tmp = self.packed_str(tmp)
            outArr[i] = tmp 
        
        return(outArr)

    ########

    def set_return_num(self, num):
        flag_byte = self.binary_str_arr(self.get_flag_byte())
        newBits = self.binary_str_arr(num, 3)
        outByte = self.bitpack((newBits,flag_byte), ((0,3), (3,8)))
        self.set_dimension("flag_byte", outByte)
        return

    def set_num_returns(self, num):
        flag_byte = self.binary_str_arr(self.get_flag_byte())
        newBits = self.binary_str_arr(num, 3)
        outByte = self.bitpack((flag_byte,newBits,flag_byte), 
            ((0,3),(0,3), (6,8)))
        self.set_dimension("flag_byte", outByte)
        return

    def set_scan_dir_flag(self, flag): 
        flag_byte = self.binary_str_arr(self.get_flag_byte())
        newBits = self.binary_str_arr(flag, 1)
        outByte = self.bitpack((flag_byte,newBits,flag_byte), 
            ((0,6),(0,1), (7,8)))
        self.set_dimension("flag_byte", outByte)
        return

    def set_edge_flight_line(self, line):
        flag_byte = self.binary_str_arr(self.get_flag_byte())
        newBits = self.binary_str_arr(line, 1)
        outByte = self.bitpack((flag_byte,newBits), 
            ((0,7),(0,1)))
        self.set_dimension("flag_byte", outByte)
        return

    def set_raw_classification(self, classification):
        self.set_dimension("raw_classification", classification)
           
    def set_classification(self, classification):
        class_byte = self.binary_str_arr(self.get_raw_classification())
        new_bits = self.binary_str_arr(classification, 5)
        out_byte = self.bitpack((new_bits, class_byte), ((0,5),(5,8)))
        self.set_dimension("raw_classification", out_byte)
        return

    def set_synthetic(self, synthetic):
        class_byte = self.binary_str_arr(self.get_raw_classification())
        new_bits = self.binary_str_arr(synthetic, 1)
        out_byte = self.bitpack((class_byte, new_bits, class_byte),
                                   ((0,5), (0,1), (6,8)))
        self.set_dimension("raw_classification", out_byte)
        return

    def set_key_point(self, pt):
        class_byte = self.binary_str_arr(self.get_raw_classification())
        new_bits = self.binary_str_arr(pt, 1)
        out_byte = self.bitpack((class_byte, new_bits, class_byte), 
                                ((0,6),(0,1),(7,8)))
        self.set_dimension("raw_classification", out_byte)
        return
 
    def set_withheld(self, withheld):
        class_byte = self.binary_str_arr(self.get_raw_classification())
        new_bits = self.binary_str_arr(withheld, 1)
        out_byte = self.bitpack((class_byte, new_bits),
                                 ((0,7), (0,1)))
        self.set_dimension("raw_classification", out_byte)

    def set_scan_angle_rank(self, rank):
        self.set_dimension("scan_angle_rank", rank)
        return

    def set_user_data(self, data):
        self.set_dimension("user_data", data)
        return
    
    def set_pt_src_id(self, data):
        self.set_dimension("pt_src_id", data)
        return
    
    def set_gps_time(self, data):
        vsn = self.header.pt_dat_format_id
        if vsn in (1,2,3,4,5):    
            self.set_dimension("gps_time", data)
            return
        raise LaspyException("GPS Time is not available for point format: " + str(vsn))
    
    def set_red(self, red):
        vsn = self.header.pt_dat_format_id
        if vsn in (2,3,5):
            self.set_dimension("red", red)
            return
        raise LaspyException("Color Data Not Available for Point Format: " + str(vsn))

    def set_green(self, green):
        vsn = self.header.pt_dat_format_id
        if vsn in (2,3,5):
            self.set_dimension("green", green)
            return
        raise LaspyException("Color Data Not Available for Point Format: " + str(vsn))


    
    def set_blue(self, blue):
        vsn = self.header.pt_dat_format_id
        if vsn in (2,3,5):
            self.set_dimension("blue", blue)
            return
        raise LaspyException("Color Data Not Available for Point Format: " + str(vsn))

    def set_wave_packet_descp_idx(self, idx):
        vsn = self.header.pt_dat_format_id
        if vsn in (4, 5):
            self.set_dimension("wave_packet_descp_index", idx)
            return
        raise LaspyException("Waveform Packet Description Index Not Available for Point Format: " + str(vsn))

    def set_byte_offset_to_wavefm_data(self, idx):
        vsn = self.header.pt_dat_format_id
        if vsn in (4, 5):
            self.set_dimension("byte_offset_to_wavefm_data", idx)
            return
        raise LaspyException("Byte Offset To Waveform Data Not Available for Point Format: " + str(vsn))


    
    def set_wavefm_pkt_size(self, size):
        vsn = self.header.pt_dat_format_id
        if vsn in (4, 5):
            self.set_dimension("wavefm_pkt_size", size)
            return
        raise LaspyException("Waveform Packet Size Not Available for Point Format: " + str(vsn))
    
    def set_return_pt_wavefm_loc(self, loc):
        vsn = self.header.pt_dat_format_id
        if vsn in (4, 5):
            self.set_dimension("return_pt_wavefm_loc", loc)
            return
        raise LaspyException("Return Point Waveform Loc Not Available for Point Format: " + str(vsn))
    
    def set_x_t(self, x):
        vsn = self.header.pt_dat_format_id
        if vsn in (4, 5):
            self.set_dimension("X_t_5", x)
            return
        raise LaspyException("X_t Not Available for Point Format: " + str(vsn))

    def set_y_t(self, y):
        vsn = self.header.pt_dat_format_id
        if vsn in (4, 5):
            self.set_dimension("Y_t", y)
            return
        raise LaspyException("Y_t Not Available for Point Format: " + str(vsn))
    
    def set_z_t(self, z):
        vsn = self.header.pt_dat_format_id
        if vsn in (4, 5):
            self.set_dimension("Z_t_5", z)
            return
        raise LaspyException("Z_t Not Available for Point Format: " + str(vsn))

class Extender(FileManager):
    pass
    
def CreateWithHeader(filename, header, vlrs = None):
    writer = Writer()

def ModifyWithHeader(filename, header):
    pass

def ReadWithHeader(filename, header):
    pass
