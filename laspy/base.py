import mmap
from header import HeaderManager, Header, leap_year, VLR
import datetime
from struct import pack, unpack, Struct
from util import *
from types import GeneratorType
import numpy as np



class DataProvider():
    '''Provides access to the file object, the memory map, and the numpy point map.'''
    def __init__(self, filename, manager):
        '''Construct the data provider. _mmap refers to the memory map, and _pmap 
        refers to the numpy point map.'''
        self.filename = filename
        self.fileref = False
        self._mmap = False
        self._pmap = False
        self.manager = manager
        self.mode = manager.mode
    
    def open(self, mode):
        '''Open the file, catch simple problems.'''
        try:
            self.fileref = open(self.filename, mode)
        except(Exception):
            raise LaspyException("Error opening file")

    def point_map(self):
        '''Create the numpy point map based on the point format.'''
        if type(self._mmap) == bool:
            self.map()
        self.pointfmt = np.dtype([("point", zip([x.name for x in self.manager.point_format.specs],
                                [x.np_fmt for x in self.manager.point_format.specs]))])
 
        self._pmap = np.frombuffer(self._mmap, self.pointfmt, 
                        offset = self.manager.header.data_offset)
    def close(self, flush = True):
        '''Close the data provider and flush changes if _mmap and _pmap exist.''' 
        if flush and self.manager.has_point_records: 
            if type(self._mmap) != bool:
                try:
                    self._mmap.flush()
                    self._mmap.close()
                    self._mmap = False
                    self._pmap = False
                except(Exception):
                    raise LaspyException("Error closing mmap")
        self._mmap = False
        self._pmap = False
        if self.fileref != False:
            try:
                self.fileref.close()
            except(Exception):
                raise LaspyException("Error closing file.")

    def map(self):
        '''Memory map the file'''
        if self.fileref == False:
            raise LaspyException("File not opened.")
        try:
            if self.mode == "r":
                self._mmap = mmap.mmap(self.fileref.fileno(), 0, access = mmap.ACCESS_READ)
            elif self.mode in ("w", "rw"):
                self._mmap = mmap.mmap(self.fileref.fileno(), 0, access = mmap.ACCESS_WRITE)
            else:
                raise LaspyException("Invalid Mode: " + str(self.mode))
        except(Exception): 
            raise LaspyException("Error mapping file.")

    def remap(self,flush = True, point_map = False):
        '''Re-map the file. Flush changes, close, open, and map. Optionally point map.'''
        if flush and type(self._mmap) != bool: 
            self._mmap.flush() 
        self.close(flush=False)
        self.open("r+b")
        self.map()
        if point_map: 
            self.point_map()
   
    def __getitem__(self, index):
        '''Return the raw bytes corresponding to the point @ index.'''
        try:
            index.stop
        except AttributeError:
            return(self._pmap[index][0])
        if index.step:
            step = index.step
        else:
            step = 1
        return([x[0] for x in self._pmap[index.start:index.stop,step]])

    def __setitem__(self, key, value):
        '''Assign raw bytes for point @ key'''
        try:
            key.stop
        except AttributeError:
            self._pmap[key] = (value,)
            return
        self._pmap[key.start:key.stop] = [(x,) for x in value]

    def filesize(self):
        '''Return the size ofs the current map'''
        if self._mmap == False:
            raise LaspyException("File not mapped")
        return(self._mmap.size())

class FileManager():
    '''Superclass of Reader and Writer, provides most of the data manipulation functionality in laspy.''' 
    def __init__(self,filename, mode, header = False, vlrs = False): 
        '''Build the FileManager object. This is done when opening the file
        as well as upon completion of file modification actions like changing the 
        header padding.'''
        self.vlr_formats = Format("VLR")
        self.mode = mode
        self.data_provider = DataProvider(filename, self) 
        self.setup_memoizing()

        self.calc_point_recs = False

        self.point_refs = False
        self._current = 0 

        if self.mode in ("r", "rw"):
            self.setup_read_write(vlrs)
            return

        elif self.mode == "w":
            self.setup_write(header, vlrs)
            return
        else:
            raise LaspyException("Append Mode Not Supported")
        
    def setup_read_write(self, vlrs):
        self.data_provider.open("r+b")
        self.data_provider.map() 
        self.header_format = Format("h" + self.grab_file_version())
        self.vlr_formats = Format("VLR")
        self.get_header()
        self.populate_vlrs()
        self.point_refs = False
        self.has_point_records = True
        self._current = 0
        self.point_format = Format(self.header.data_format_id) 
        self.data_provider.point_map()
        if vlrs != False:
            self.set_vlrs(vlrs)
        return

    def setup_write(self,header, vlrs):
        if header == False:
            raise LaspyException("Write mode requires a valid header object.")
        ## No file to store data yet.
        self.has_point_records = False
        self.data_provider.open("w+b") 
        self.header_format = header.format 
        self._header = header
        self.header = HeaderManager(header = header, reader = self)

        #if self._header.data_format_id != None:
        #    self.point_format = Format(str(self._header.data_format_id))
        #else:
        #    self.point_format = Format("0")
        self.point_format = Format(self._header.data_format_id)

        self.initialize_file_padding(vlrs)

        ## We have a file to store data now.
        self.data_provider.remap()
        self.header.flush()
        if not vlrs in [[], False]:
            self.set_vlrs(vlrs)
        if self._header.created_year == 0:
            self.header.date = datetime.datetime.now()
        
        if vlrs != False:
            self.set_vlrs(vlrs) 
        self.populate_vlrs()
        
        return


    def initialize_file_padding(self, vlrs):
        filesize = self._header.format.rec_len
        if vlrs != False:
            filesize += sum([len(x) for x in vlrs])
        self.vlr_stop = filesize
        if self._header.data_offset != 0:
            filesize = max(self._header.data_offset, filesize)
        self._header.data_offset = filesize 
        self.data_provider.fileref.write("\x00"*filesize)
        return

    def setup_memoizing(self):
        self.header_changes = set()
        self.header_properties = {}

    def populate_c_packers(self):
        '''This is depricated if the numpy point map is used, because nparr.tostring() is MUCH faster.
        This creates compiled Struct objects for various formats.
        '''
        for spec in self.point_format.specs:
            self.c_packers[spec.name] = Struct(spec.fmt)
            self.c_packers[spec.fmt] = self.c_packers[spec.name]
    
    def packed_str(self, string):
        '''Take a little endian binary string, and convert it to a python int.'''
        return(sum([int(string[idx])*(2**idx) for idx in xrange(len(string))]))

    def binary_str(self,N, zerolen = 8):
        '''Take a python integer and create a binary string padded to len zerolen.'''
        raw_bin = bin(N)[2:][::-1]
        padding = zerolen-len(raw_bin)
        if padding < 0:
            raise LaspyException("Invalid Data: Packed Length is Greater than allowed.")
        return(raw_bin + '0'*(zerolen-len(raw_bin)))

    def read(self, bytes):
        '''Wrapper for mmap.mmap read function'''
        return(self.data_provider._mmap.read(bytes))
    
    def reset(self):
        '''Refresh the mmap and fileref'''
        self.data_provier.remap() 
        return
     
    def seek(self, bytes, rel = True):
        '''Wrapper for mmap.mmap seek functions, make option rel explicit'''
        self._current = None
        if rel:
            self.data_provider._mmap.seek(bytes,1)
            return
        self.data_provider._mmap.seek(bytes, 0)
        
    def read_words(self, name):
        '''Read a consecutive sequence of packed binary data, return a single 
        element or list.'''
        try:
            dim = self.vlr_formats.lookup[name]
        except KeyError:
            raise LaspyException("Dimension " + name + " not found.")
        return(self._read_words(dim.fmt, dim.num, dim.length))

    def _read_words(self, fmt, num, bytes):
        '''Read a consecutive sequence of packed binary data, return a single
        element or list'''
        outData = []
        for i in xrange(num):
            dat = self.read(bytes)
            outData.append(unpack(fmt, dat)[0])
        if len(outData) > 1:
            return(outData)
        return(outData[0])
    
    def _pack_words(self, fmt, num, bytes, val):
        if num == 1:
            return(pack(fmt, val))
        outData = "".join([pack(fmt, val[i]) for i in xrange(num)])
        return(outData)


    def grab_file_version(self):
        '''Manually grab file version from header'''
        self.seek(24, rel = False)
        v1 = self._read_words("<B", 1, 1)
        v2 = self._read_words("<B", 1, 1)
        self.seek(0, rel = True)
        return(str(v1) +"." +  str(v2))

    def get_header(self):
        '''Return the header object, or create one if absent.'''
        ## Why is this != neccesary?
        try:
            return(self.header)
        except:
            self.header = HeaderManager(header = Header(), reader = self)
            return(self.header)

    def populate_vlrs(self): 
        '''Catalogue the variable length records'''
        self.vlrs = []
        self.seek(self.header.header_size, rel = False)
        for i in xrange(self.get_header_property("num_variable_len_recs")): 
            new_vlr = VLR(None, None, None)
            new_vlr.build_from_reader(self)
            self.vlrs.append(new_vlr)
            if self.data_provider._mmap.tell() > self.header.data_offset:
                self.seek(self.header.data_offset, rel = False)
                raise LaspyException("Error, Calculated Header Data "
                    "Overlaps The Point Records!")
        self.vlr_stop = self.data_provider._mmap.tell()
        self.header.__dict__["vlrs"] = self.vlrs
        return

    def get_vlrs(self):
        '''Populate and return list of :obj:`laspy.header.VLR` objects`.'''
        self.populate_vlrs()
        return(self.vlrs)
    
    def get_padding(self):
        '''Return the padding between the end of the VLRs and the beginning of
        the point records'''
        return(self.header.data_offset - self.vlr_stop)

    def get_pointrecordscount(self):
        '''calculate the number of point records'''
        if self.calc_point_recs != False:
            return(self.calc_point_recs)
        
        if self.header.get_version != "1.3":
            try:
                return(len(self.data_provider._pmap))
            except:
                new_val =  ((self.data_provider._mmap.size()-
                    self.header.data_offset)/self.header.data_record_length)
                self.calc_point_recs = new_val
                return(new_val)
        else:
            raise LaspyException("Version 1.3 is currently broken due to waveform data.")
            new_val = ((self.header.StWavefmDatPktRec-
                self.header.data_offset)/self.header.data_record_length)       
            self.calc_point_recs = new_val
            return(new_val)

    def set_input_srs(self):
        pass
    
    def set_output_srsS(self):
        pass

    def get_raw_point_index(self,index):
        '''Return the byte index of point number index'''
        return(self.header.data_offset + 
            index*self.header.data_record_length)
    
    def get_points(self):
        '''Return a numpy array of all point data in a file.'''
        if not self.has_point_records:
            return None
        if type(self.point_refs) == bool:
            self.build_point_refs()
        #single_fmt = self.point_format.pt_fmt_long[1:]
        #fmtlen = len(single_fmt)
        #big_fmt_string = "".join(["<", single_fmt*self.header.point_records_count])
        #pts =  unpack(big_fmt_string, self.data_provider._mmap[self.header.data_offset:self.data_provider._mmap.size()])
        #return((Point(self, unpacked_list = pts[fmtlen*i:fmtlen*(i+1)]) for i in xrange(self.header.point_records_count)))
        #return([Point(self,x) for x in self._get_raw_dimension(0, self.header.data_record_length)])
        #return((x[0] for x in self.data_provider._pmap))
        return(self.data_provider._pmap)
    
    def get_raw_point(self, index):
        '''Return the raw bytestring associated with point of number index'''
        #start = (self.header.data_offset + 
        #    index * self.header.data_record_length)
        #return(self.data_provider._mmap[start : start +
        #     self.header.data_record_length])
        return(self.data_provider._pmap[index][0].tostring())


#self, reader, startIdx ,version
    def get_point(self, index, nice=False):
        '''Return point object for point of number index / #legacy_api''' 
        if index >= self.get_pointrecordscount():
            return 
        self._current = index
        return(Point(self, self.get_raw_point(index), nice= nice))

    
    def get_next_point(self):
        '''Return next point object via get_point / #legacy_api'''
        if self._current == None:
            raise LaspyException("No Current Point Specified," + 
                            " use Reader.GetPoint(0) first")
        if self._current == self.get_pointrecordscount():
            return
        return self.get_point(self._current + 1)

    def build_point_refs(self):
        '''Build array of point offsets '''
        pts = int(self.get_pointrecordscount())
        length = int(self.header.data_record_length)
        offs = int(self.header.data_offset)
        self.point_refs = [x*length + offs
                for x in xrange(pts)]
        return

    def get_dimension(self, name):
        '''Grab a point dimension by name, returning a numpy array. Refers to 
        reader.point_format for the required Spec instance.'''
        if not self.has_point_records:
            return None
        #if type(self.point_refs) == bool:
        #    self.build_point_refs()
        if type(self.data_provider._pmap) == bool:
            self.data_provider.point_map()
        try: 
            spec = self.point_format.lookup[name]
            #return(self._get_dimension(spec))
            return(self._get_dimension(spec))
        except KeyError:
            raise LaspyException("Dimension: " + str(name) + 
                            " not found.")
    
    def _get_dimension(self, spec):
        return(self.data_provider._pmap["point"][spec.name])

    def _get_dimension_by_specs(self,offs, fmt, length):
        '''Return point dimension of specified offset format and length''' 
        _mmap = self.data_provider._mmap  
        prefs = (offs + x for x in self.point_refs) 
        packer = self.c_packers[fmt]
        return((packer.unpack(_mmap[x:x+length])[0] for x in prefs))




    def _get_raw_dimension(self,spec):
        '''Return point dimension of specified offset format and length''' 
        #_mmap = self.data_provider._mmap 
        #prefs = (offs + x for x in self.point_refs)
        #return((_mmap[start + offs : start+offs+length] for start in prefs))
        return(self.data_provider._pmap["point"][spec.name].tostring())

    def _get_raw_datum(self, rec_offs, spec):
        '''return raw bytes associated with non dimension field (VLR/Header)'''
        return(self.data_provider._mmap[(rec_offs + spec.offs):(rec_offs + spec.offs 
                        + spec.num*spec.length)])

    def _get_datum(self, rec_offs, spec):
        '''Return unpacked data assocaited with non dimension field (VLR/Header)'''
        data = self._get_raw_datum(rec_offs, spec)
        if spec.num == 1:
            return(unpack(spec.fmt, data)[0])
        unpacked = map(lambda x: unpack(spec.fmt, 
            data[x*spec.length:(x+1)*spec.length])[0], xrange(spec.num))
        if spec.pack:
            return("".join([str(x[0]) for x in unpacked]))
        return(unpacked) 

    def get_raw_header_property(self, name):
        '''Wrapper for grabbing raw header bytes with _get_raw_datum'''
        spec = self.header_format.lookup[name]
        return(self._get_raw_datum(0, spec))
    
    def get_header_property(self, name):
        '''Wrapper for grabbing unpacked header data with _get_datum'''
        if name in self.header_changes:
            spec = self.header_format.lookup[name]
            new_val = self._get_datum(0, spec)
            self.header_properties[name] = new_val
            self.header_changes.remove(name)
            return(new_val)
        elif name in self.header_properties:
            return(self.header_properties[name])
        else:
            spec = self.header_format.lookup[name]
            val = self._get_datum(0, spec)
            self.header_properties[name] = val
            return(val)

    ### To Implement: Scale            
    
    def get_x(self, scale=False):
        if not scale:
            return(self.get_dimension("X"))
        return(self.get_dimension("X")*self.header.scale[0] + self.header.offset[0])

    def get_y(self, scale=False):
        if not scale:
            return(self.get_dimension("Y"))
        return(self.get_dimension("Y")*self.header.scale[1] + self.header.offset[1])

    def get_z(self, scale=False):
        if not scale:
            return(self.get_dimension("Z"))
        return(self.get_dimension("Z")*self.header.scale[2] + self.header.offset[2])
    
    def get_intensity(self):
        return(self.get_dimension("intensity"))
    
    def get_flag_byte(self):
        return(self.get_dimension("flag_byte"))
    
    def get_return_num(self):
        rawDim = self.get_flag_byte()
        return(np.array([self.packed_str(self.binary_str(x)[0:3]) for x in rawDim])) 

    def get_num_returns(self):
        rawDim = self.get_flag_byte()
        return(np.array([self.packed_str(self.binary_str(x)[3:6]) for x in rawDim]))  

    def get_scan_dir_flag(self):
        rawDim = self.get_flag_byte()
        return(np.array([self.packed_str(self.binary_str(x)[6]) for x in rawDim])) 

    def get_edge_flight_line(self):
        rawDim = self.get_flag_byte()
        return(np.array(([self.packed_str(self.binary_str(x)[7]) for x in rawDim])))
    
    def get_raw_classification(self):
        return(self.get_dimension("raw_classification"))
    
    def get_classification(self): 
        return(np.array([self.packed_str(self.binary_str(x)[0:5]) 
                for x in self.get_raw_classification()])) 

    def get_synthetic(self):
        return(np.array([self.packed_str(self.binary_str(x)[5]) 
                for x in self.get_raw_classification()])) 

    def get_key_point(self):
        return(np.array([self.packed_str(self.binary_str(x)[6]) 
                for x in self.get_raw_classification()])) 

    def get_withheld(self):
        return(np.array([self.packed_str(self.binary_str(x)[7]) 
                for x in self.get_raw_classification()])) 
    
    def get_scan_angle_rank(self):
        return(self.get_dimension("scan_angle_rank"))
    
    def get_user_data(self):
        return(self.get_dimension("user_data"))
    
    def get_pt_src_id(self):
        return(self.get_dimension("pt_src_id"))
    
    def get_gps_time(self):
        fmt = self.header.data_format_id
        if fmt in (1,2,3,4,5):
            return(self.get_dimension("gps_time"))
        raise LaspyException("GPS Time is not defined on pt format: "
                        + str(fmt))
    

    def get_red(self):
        fmt = self.header.data_format_id
        if fmt in (2,3,5):
            return(self.get_dimension("red"))
        raise LaspyException("Color is not available for point format: " + str(fmt))
    
    def get_green(self):
        fmt = self.header.data_format_id
        if fmt in (2,3,5):
            return(self.get_dimension("green"))
        raise LaspyException("Color is not available for point format: " + str(fmt))

    
    def get_blue(self):
        fmt = self.header.data_format_id
        if fmt in (2,3,5):
            return(self.get_dimension("blue"))
        raise LaspyException("Color is not available for point format: " + str(fmt))


    def get_wave_packet_descp_idx(self):
        fmt = self.header.data_format_id
        if fmt in (4, 5):
            return(self.get_dimension("wave_packet_descp_idx"))
        raise LaspyException("Wave Packet Description Index Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def get_byte_offset_to_wavefm_data(self):
        fmt = self.header.data_format_id
        if fmt in (4, 5):
            return(self.get_dimension("byte_offset_to_wavefm_data"))
        raise LaspyException("Byte Offset to Waveform Data Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def get_wavefm_pkt_size(self):
        fmt = self.header.data_format_id
        if fmt in (4, 5):
            return(self.get_dimension("wavefm_pkt_size"))
        raise LaspyException("Wave Packet Description Index Not"
                       + " Available for Pt Fmt: " + str(fmt))

    def get_return_pt_wavefm_loc(self):
        fmt = self.header.data_format_id
        if fmt in (4, 5):
            return(self.get_dimension("return_pt_wavefm_loc"))
        raise LaspyException("Return Pointt Waveformm Loc Not"
                       + " Available for Pt Fmt: " +str(fmt))

    def get_x_t(self):
        fmt = self.header.data_format_id
        if fmt in (4, 5):
            return(self.get_dimension("X_t"))
        raise LaspyException("X(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

    def get_y_t(self):
        fmt = self.header.data_format_id
        if fmt in (4, 5):
            return(self.get_dimension("Y_t"))
        raise LaspyException("Y(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

    def get_z_t(self):
        fmt = self.header.data_format_id
        if fmt in (4, 5):
            return(self.get_dimension("Z_t"))
        raise LaspyException("Z(t) Not"
                       + " Available for Pt Fmt: " +str(fmt))

class Reader(FileManager):
    def close(self):
        '''Close the file.'''
        self.data_provider.close() 
    
    def __del__(self):
        self.close()


class Writer(FileManager):

    def close(self, ignore_header_changes = False):
        '''Flush changes to mmap and close mmap and fileref''' 
        if not ignore_header_changes:
            self.header.update_histogram()
            self.header.update_min_max() 
        self.data_provider.close()
   
    def __del__(self): 
        self.close()

    def set_vlrs(self, value): 
        if value == False or len(value) == 0:
            return
        if not all([x.isVLR for x in value]):
            raise LaspyException("set_vlrs requers an iterable object " + 
                        "composed of :obj:`laspy.header.VLR` objects.")
        elif self.mode == "w+":
            raise NotImplementedError
        elif self.mode == "rw": 
            current_size = self.data_provider._mmap.size()
            current_padding = self.get_padding()
            old_offset = self.header.data_offset
            new_offset = current_padding + self.header.header_size + sum([len(x) for x in value])
            self.set_header_property("data_offset", new_offset)
            self.set_header_property("num_variable_len_recs", len(value))
            self.data_provider.fileref.seek(0, 0)
            dat_part_1 = self.data_provider.fileref.read(self.header.header_size)
            self.data_provider.fileref.seek(old_offset, 0)
            dat_part_2 = self.data_provider.fileref.read(current_size - old_offset)
            # Manually Close:
            self.data_provider.close(flush=False)
            self.data_provider.open("w+b")
            self.data_provider.fileref.write(dat_part_1)
            for vlr in value:
                byte_string = vlr.to_byte_string()
                self.data_provider.fileref.write(byte_string)
            self.data_provider.fileref.write("\x00"*current_padding)
            self.data_provider.fileref.write(dat_part_2)
            self.data_provider.fileref.close()
            self.data_provider.open("r+b")
            self.data_provider.map()
            self.data_provider.point_map()
        elif self.mode == "w" and not self.has_point_records:
            self.seek(self.header.header_size, rel = False)
            for vlr in value: 
                self.data_provider._mmap.write(vlr.to_byte_string())
            return
        else:
            raise(LaspyException("set_vlrs requires the file to be opened in a " + 
                "write mode, and must be performed before point information is provided." + 
                "Try closing the file and opening it in rw mode. "))

    def set_padding(self, value):
        '''Set the padding between end of VLRs and beginning of point data'''
        if value < 0: 
            raise LaspyException("New Padding Value Overwrites VLRs")
        if self.mode == "w":
            if not self.has_point_records:
                self.data_provider.fileref.seek(self.vlr_stop, 0)
                self.data_provider.fileref.write("\x00"*value)
                self.data_provider.remap()
                return
            else:
                raise NotImplementedError
        elif self.mode == "rw":
            old_offset = self.header.data_offset
            self.set_header_property("data_offset",
                                            self.vlr_stop +  value)
            #self.header.data_offset = self.vlr_stop + value 
            self.data_provider._mmap.flush() 
            self.seek(0, rel=False)
            dat_part_1 = self.data_provider._mmap.read(self.vlr_stop)
            self.seek(old_offset, rel = False)
            dat_part_2 = self.data_provider._mmap.read(len(self.data_provider._mmap) - old_offset) 
            self.data_provider.close() 
            self.data_provider.open("w+b") 
            self.data_provider.fileref.write(dat_part_1) 
            self.data_provider.fileref.write("\x00"*value)
            self.data_provider.fileref.write(dat_part_2)
            self.data_provider.close()
            self.__init__(self.data_provider.filename, self.mode) 
            return(len(self.data_provider._mmap))
        elif self.mode == "r+":
            pass
        else:
            raise(LaspyException("Must be in write mode to change padding."))
        return(len(self.data_provider._mmap))
    
    def pad_file_for_point_recs(self,num_recs): 
        '''Pad the file with null bytes out to a calculated length based on 
        the data given. This is usually a side effect of set_dimension being 
        called for the first time on a file in write mode. '''
        bytes_to_pad = num_recs * self.point_format.rec_len
        #old_size = self.data_provider.filesize()
        old_size = self.header.data_offset 
        self.data_provider._mmap.flush()
        self.data_provider.fileref.seek(old_size, 0)
        self.data_provider.fileref.write("\x00" * (bytes_to_pad))
        self.data_provider.fileref.flush()
        self.data_provider.remap(flush = False, point_map = True) 
        # Write Phase complete, enter rw mode?
        
        return

    def set_dimension(self, name,new_dim):
        '''Set a dimension (X,Y,Z etc) to the given value.'''
        #if not "__len__" in dir(new_dim):
        if isinstance(new_dim, GeneratorType):
            new_dim = list(new_dim)

        if not self.has_point_records:
            self.has_point_records = True
            self.set_header_property("point_records_count", len(new_dim))
            self.pad_file_for_point_recs(len(new_dim)) 
        ptrecs = self.get_pointrecordscount()
        if len(new_dim) != ptrecs:
            raise LaspyException("Error, new dimension length (%s) does not match"%str(len(new_dim)) + " the number of points (%s)" % str(ptrecs))
        try:
            spec = self.point_format.lookup[name]
            return(self._set_dimension(spec, new_dim))
        except KeyError:
            raise LaspyException("Dimension: " + str(name) + 
                            "not found.")
 
    def _set_dimension(self, spec, value):
        self.data_provider._pmap["point"][spec.name] = value
        return

    def _set_dimension_by_spec(self,new_dim,offs, fmt, length):
        '''Set a point dimension of appropriate offset format and length to new_dim'''
        if type(self.point_refs) == bool:
            self.build_point_refs()
        _mmap = self.data_provider._mmap
        packer = self.c_packers[fmt]
        i = 0
        for start in self.point_refs:
            _mmap[start+offs:start+offs+length] = packer.pack(new_dim[i])
            i += 1

        #idx = xrange(self.calc_point_recs)
        #starts = (self.point_refs[i] + offs for i in idx) 
        #def f_set(x):
        #    i = starts.next()
        #    #self.seek(i, rel = False)
        #    #self.data_provider._mmap.write(pack(fmt, new_dim[x]))
        #    self.data_provider._mmap[i:i + length] = pack(fmt,new_dim[x])
        #map(f_set, idx) 
        
        # Is this desireable
        #self.data_provider._mmap.flush()    def write_bytes(self, idx, bytes):
        return True
    
    def set_points(self, points):
        '''Set the point data for the file, using either a list of laspy.util.Point
        instances, or a numpy array of point data (as recieved from get_points).'''
        if isinstance(points, GeneratorType):
            points = list(points)
        if not self.has_point_records:
            self.has_point_records = True
            self.pad_file_for_point_recs(len(points))
        if isinstance(points[0], Point):
            self.data_provider._mmap[self.header.data_offset:self.data_provider._mmap.size()] = b"".join([x.pack() for x in points])
            self.data_provider.point_map()
        else:
             #self.data_provider._mmap[self.header.data_offset:self.data_provider._mmap.size()] = points.tostring()
             #self.data_provider._pmap["point"] = points["point"]
             self.data_provider._pmap[:] = points[:]
             #self.data_provider.point_map()
        #single_fmt = self.point_format.pt_fmt_long[1:]
        #big_fmt_string = "".join(["<", single_fmt*self.header.point_records_count]) 
        #out = []
        #(point.unpacked for point in points)
        #for i in points: 
        #    out.extend(i.unpacked)
        #bytestr = pack(big_fmt_string, *out)
        #self.data_provider._mmap[self.header.data_offset:self.data_provider._mmap.size()] = bytestr

    def _set_raw_points(self, new_raw_points):
        if not self.has_point_records:
            self.has_point_records = True
            self.pad_file_for_point_recs(len(new_raw_points))
        '''Set a point dimension of appropriate name to new_dim'''
        ptrecs = self.get_pointrecordscount()
        if len(new_raw_points) != ptrecs:
            raise LaspyException("Error, new dimension length (%s) does not match"%str(len(new_raw_points)) + " the number of points (%s)" % str(ptrecs)) 
        if type(self.point_refs) == bool:
            self.build_point_refs()
        idx = (xrange(len(self.point_refs)))
        def f(x):
            self.data_provider._mmap[self.point_refs[x]:self.point_refs[x] 
                    + self.header.data_record_length] = new_raw_points[x]
        map(f, idx)
        self.data_provider.point_map()

    def _set_raw_datum(self, rec_offs, spec, val):
        '''Set a non dimension field with appropriate record type offset (0 for header)
        , appropriate spec object, and a new value. Uses raw bytes.'''
        self.data_provider._mmap[rec_offs+spec.offs:rec_offs+spec.offs +
                  spec.num*spec.length] = val
        return
    
    def _set_datum(self, rec_offs, dim, val):
        '''Set a non dimension field as with _set_raw_datum, but supply a formatted value''' 
        if dim.num == 1:
            lb = rec_offs + dim.offs
            ub = lb + dim.length 
            try:
                self.data_provider._mmap[lb:ub] = pack(dim.fmt, val)
            except:
                self.data_provider._mmap[lb:ub] = pack(dim.fmt, int(val))

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
            try:
                outbyte = pack(dim.fmt, val[x])
            except:
                outbyte = pack(dim.fmt, int(val[x]))
            self.data_provider._mmap[(x*dim.length + rec_offs + 
                    dim.offs):((x+1)*dim.length + rec_offs 
                    + dim.offs)]=outbyte
        map(f, xrange(dim.num))
        return

    def set_raw_header_property(self, name, value):
        '''Wrapper for _set_raw_datum, accpeting name of header property and raw byte value. '''
        try:
            spec = self.header_format.lookup[name]
        except(KeyError):
            raise(LaspyException("Header Dimension: " + 
                  str(name) + " not found."))
        self._set_raw_datum(0, spec, value)

    def set_header_property(self, name, value):
        '''Wrapper for _set_datum, accepting name of header property and formatted value'''
        try:
            dim = self.header_format.lookup[name]
        except(KeyError):
            raise LaspyException("Header Dimension: " + str(name) + " not found.")
        if not dim.overwritable:
            raise(LaspyException("Field " + dim.name + " is not overwritable."))
        
        self._set_datum(0, dim, value)
        self.header_changes.add(name)
        return

    def set_header(self, header):
        raise NotImplementedError
    
    def set_input_srs(self, srs):
        raise NotImplementedError
    
    def set_output_srs(self, srs):
        raise NotImplementedError

    ##  To Implement: Scale
    def set_x(self,X, scale = False):
        '''Wrapper for set_dimension("X", new_dimension)'''
        if not scale:
            self.set_dimension("X", X)
            return
        self.set_dimension("X", np.round((X - self.header.offset[0])/self.header.scale[0]))
        return

    def set_y(self,Y, scale = False):
        '''Wrapper for set_dimension("Y", new_dimension)'''
        if not scale:
            self.set_dimension("Y", Y)
            return
        self.set_dimension("Y", np.round((Y - self.header.offset[1])/self.header.scale[1]))
        return

    def set_z(self, Z, scale = False):
        '''Wrapper for set_dimension("Z", new_dimension)'''
        if not scale:
            self.set_dimension("Z", Z)
            return
        self.set_dimension("Z", np.round((Z-self.header.offset[2])/self.header.scale[2]))
        return

    def set_intensity(self, intensity):
        '''Wrapper for set_dimension("intensity", new_dimension)'''
        self.set_dimension("intensity", intensity)
        return
    
    def set_flag_byte(self, byte):
        '''Wrapper for set_dimension("flag_byte", new_dimension)'''
        self.set_dimension("flag_byte", byte)
        return
    
    # Utility Functions, refactor
    
    def binary_str_arr(self, arr, length = 8):
        '''Convert an array of numeric data to an array of binary strings'''
        return([self.binary_str(x, length) for x in arr])

    def bitpack(self,arrs,idx, pack = True):
        '''Pack an array of binary strings into a byte based on idx
        for example bitpack((str1, str2), (0,3), (3,8)) packs the length-8
        binary strings str1 and str2 into a byte, using the first three bits
        of str1, and the last five bits of str2. 
        
        There is probably a more efficient way of doing this.
        '''
        if pack:
            outArr = ([1]*len(arrs[0]))
        else:
            outArr = (["0"*8]*len(arrs[0]))
       
        for i in xrange(len(arrs[0])):
            tmp = ""
            tmp = []
            j = 0
            for arr in arrs:
                tmp.append(arr[i][idx[j][0]:idx[j][1]])
                j += 1
            tmp = "".join(tmp)
            if pack:
                tmp = self.packed_str(tmp)
            outArr[i] = tmp 
        
        return(outArr)

    ########

    def set_return_num(self, num):
        '''Set the binary field return_num in the flag_byte'''
        flag_byte = self.binary_str_arr(self.get_flag_byte())
        newBits = self.binary_str_arr(num, 3)
        outByte = self.bitpack((newBits,flag_byte), ((0,3), (3,8)))
        self.set_dimension("flag_byte", outByte)
        return

    def set_num_returns(self, num):
        '''Set the binary field num_returns in the flag_byte'''
        flag_byte = self.binary_str_arr(self.get_flag_byte())
        newBits = self.binary_str_arr(num, 3)
        outByte = self.bitpack((flag_byte,newBits,flag_byte), 
            ((0,3),(0,3), (6,8)))
        self.set_dimension("flag_byte", outByte)
        return

    def set_scan_dir_flag(self, flag): 
        '''Set the binary field scan_dir_flag in the flag_byte'''
        flag_byte = self.binary_str_arr(self.get_flag_byte())
        newBits = self.binary_str_arr(flag, 1)
        outByte = self.bitpack((flag_byte,newBits,flag_byte), 
            ((0,6),(0,1), (7,8)))
        self.set_dimension("flag_byte", outByte)
        return

    def set_edge_flight_line(self, line):
        '''Set the binary field edge_flight_line in the flag_byte'''
        flag_byte = self.binary_str_arr(self.get_flag_byte())
        newBits = self.binary_str_arr(line, 1)
        outByte = self.bitpack((flag_byte,newBits), 
            ((0,7),(0,1)))
        self.set_dimension("flag_byte", outByte)
        return

    def set_raw_classification(self, classification):
        '''Set the entire classification byte at once. This is faster than setting the binary fields individually, 
        but care must be taken that the values mean what you think they do. '''
        self.set_dimension("raw_classification", classification)
           
    def set_classification(self, classification):
        '''Set the binary classification field inside the raw classification byte'''
        class_byte = self.binary_str_arr(self.get_raw_classification())
        new_bits = self.binary_str_arr(classification, 5)
        out_byte = self.bitpack((new_bits, class_byte), ((0,5),(5,8)))
        self.set_dimension("raw_classification", out_byte)
        return

    def set_synthetic(self, synthetic):
        '''Set the binary field synthetic inside the raw classification byte'''
        class_byte = self.binary_str_arr(self.get_raw_classification())
        new_bits = self.binary_str_arr(synthetic, 1)
        out_byte = self.bitpack((class_byte, new_bits, class_byte),
                                   ((0,5), (0,1), (6,8)))
        self.set_dimension("raw_classification", out_byte)
        return

    def set_key_point(self, pt):
        '''Set the binary key_point field inside the raw classification byte'''
        class_byte = self.binary_str_arr(self.get_raw_classification())
        new_bits = self.binary_str_arr(pt, 1)
        out_byte = self.bitpack((class_byte, new_bits, class_byte), 
                                ((0,6),(0,1),(7,8)))
        self.set_dimension("raw_classification", out_byte)
        return
 
    def set_withheld(self, withheld):
        '''Set the binary field withheld inside the raw classification byte'''
        class_byte = self.binary_str_arr(self.get_raw_classification())
        new_bits = self.binary_str_arr(withheld, 1)
        out_byte = self.bitpack((class_byte, new_bits),
                                 ((0,7), (0,1)))
        self.set_dimension("raw_classification", out_byte)

    def set_scan_angle_rank(self, rank):
        '''Wrapper for set_dimension("scan_angle_rank")'''
        self.set_dimension("scan_angle_rank", rank)
        return

    def set_user_data(self, data):
        '''Wrapper for set_dimension("user_data")'''
        self.set_dimension("user_data", data)
        return
    
    def set_pt_src_id(self, data):
        '''Wrapper for set_dimension("pt_src_id")'''
        self.set_dimension("pt_src_id", data)
        return
    
    def set_gps_time(self, data):
        '''Wrapper for set_dimension("gps_time")'''
        vsn = self.header.data_format_id
        if vsn in (1,2,3,4,5):    
            self.set_dimension("gps_time", data)
            return
        raise LaspyException("GPS Time is not available for point format: " + str(vsn))
    
    def set_red(self, red):
        '''Wrapper for set_dimension("red")'''
        vsn = self.header.data_format_id
        if vsn in (2,3,5):
            self.set_dimension("red", red)
            return
        raise LaspyException("Color Data Not Available for Point Format: " + str(vsn))

    def set_green(self, green):
        '''Wrapper for set_dimension("green")'''
        vsn = self.header.data_format_id
        if vsn in (2,3,5):
            self.set_dimension("green", green)
            return
        raise LaspyException("Color Data Not Available for Point Format: " + str(vsn))


    
    def set_blue(self, blue):
        '''Wrapper for set_dimension("blue")'''
        vsn = self.header.data_format_id
        if vsn in (2,3,5):
            self.set_dimension("blue", blue)
            return
        raise LaspyException("Color Data Not Available for Point Format: " + str(vsn))

    def set_wave_packet_descp_idx(self, idx):
        '''Wrapper for set_dimension("wave_packet_descp_idx") This is not currently functional, 
        since addition of waveform data broke the numpy point map.'''
        vsn = self.header.data_format_id
        if vsn in (4, 5):
            self.set_dimension("wave_packet_descp_index", idx)
            return
        raise LaspyException("Waveform Packet Description Index Not Available for Point Format: " + str(vsn))

    def set_byte_offset_to_wavefm_data(self, idx):
        '''Wrapper for set_dimension("byte_offset_to_wavefm_data"), not currently functional,
        because addition of waveform data broke the numpy point map.'''
        vsn = self.header.data_format_id
        if vsn in (4, 5):
            self.set_dimension("byte_offset_to_wavefm_data", idx)
            return
        raise LaspyException("Byte Offset To Waveform Data Not Available for Point Format: " + str(vsn))


    
    def set_wavefm_pkt_size(self, size):
        '''Wrapper for set_dimension("wavefm_pkt_size"), not currently functional, because
        addition of waveform data broke the numpy point map.'''
        vsn = self.header.data_format_id
        if vsn in (4, 5):
            self.set_dimension("wavefm_pkt_size", size)
            return
        raise LaspyException("Waveform Packet Size Not Available for Point Format: " + str(vsn))
    
    def set_return_pt_wavefm_loc(self, loc):
        '''Wrapper for set_dimension("return_pt_wavefm_loc"), not currently functional,
        because addition of waveform data broke the numpy point map.'''
        
        vsn = self.header.data_format_id
        if vsn in (4, 5):
            self.set_dimension("return_pt_wavefm_loc", loc)
            return
        raise LaspyException("Return Point Waveform Loc Not Available for Point Format: " + str(vsn))
    
    def set_x_t(self, x):
        '''Wrapper for set_dimension("X_t")'''
        vsn = self.header.data_format_id
        if vsn in (4, 5):
            self.set_dimension("X_t", x)
            return
        raise LaspyException("X_t Not Available for Point Format: " + str(vsn))

    def set_y_t(self, y):
        '''Wrapper for set_dimension("Y_t")'''
        vsn = self.header.data_format_id
        if vsn in (4, 5):
            self.set_dimension("Y_t", y)
            return
        raise LaspyException("Y_t Not Available for Point Format: " + str(vsn))
    
    def set_z_t(self, z):
        '''Wrapper for set_dimension("Z_t")'''
        vsn = self.header.data_format_id
        if vsn in (4, 5):
            self.set_dimension("Z_t", z)
            return
        raise LaspyException("Z_t Not Available for Point Format: " + str(vsn))
