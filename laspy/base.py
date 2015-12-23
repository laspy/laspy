import mmap
import laspy
import os
import datetime
import struct
import util
from types import GeneratorType
import numpy as np
import copy


def read_compressed(filename):
    import subprocess
    pathvar1 = any([os.path.isfile(x + "/laszip") 
            for x in os.environ["PATH"].split(os.pathsep)])
    pathvar2 = any([os.path.isfile(x + "/laszip.exe") 
            for x in os.environ["PATH"].split(os.pathsep)])
    if (not pathvar1 and not pathvar2):
        raise(laspy.util.LaspyException("Laszip was not found on the system"))

    prc=subprocess.Popen(["laszip", "-olas", "-stdout", "-i", filename],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1)
    data, stderr=prc.communicate()
    if prc.returncode != 0:
        # What about using the logging module instead of prints?
        print("Unusual return code from laszip: %d" %prc.returncode)
        if stderr and len(stderr)<2048:
            print(stderr)
        raise ValueError("Unable to read compressed file!")
    return data
 

class FakeMmap(object):
    '''
    An object imitating a memory mapped file,
    constructed from 'buffer like' data.
    '''
    def __init__(self, filename, pos=0):
        data = read_compressed(filename)
        self.view = memoryview(data)
        self.pos = pos
        # numpy needs this, unfortunately
        self.__buffer__ = buffer(data)

    def __len__(self):
        return len(self.view)
    
    def __getitem__(self, i):
        return self.view[i]
    
    def close(self):
        self.view = None
    
    def flush(self):
        pass
    
    def seek(self, nbytes, whence=0):
        if whence == 0:
            self.pos = nbytes
        else:
            self.pos += nbytes

            
    def read(self, nbytes):
        out = self.view[self.pos:self.pos+nbytes]
        self.pos += nbytes
        return(out)
        
    def tell(self):
        return self.pos
  


class DataProvider():
    '''Provides access to the file object, the memory map, and the numpy point map.'''
    def __init__(self, filename, manager):
        '''Construct the data provider. _mmap refers to the memory map, and _pmap 
        refers to the numpy point map.'''
        self.filename = filename
        self.fileref = False
        self._mmap = False
        self._pmap = False
        self._evlrmap = False
        self.manager = manager
        self.mode = manager.mode
        # Figure out if this file is compressed
        if self.mode in ("w"):
            self.compressed = False
        else:
            try:
                tmpref = open(filename, "rb")
                tmpref.seek(104)
                fmt = int(struct.unpack("<B", tmpref.read(1))[0])
                compression_bit_7 = (fmt & 0x80) >> 7
                compression_bit_6 = (fmt & 0x40) >> 6
                if (not compression_bit_6 and compression_bit_7):
                    self.compressed = True
                else:
                    self.compressed = False
                tmpref.close()
            except Exception as e: 
                raise laspy.util.LaspyException("Error determining compression: " 
                        + str(e))

    def open(self, mode):
        '''Open the file, catch simple problems.'''
        if not self.compressed:
            try:
                self.fileref = open(self.filename, mode)
            except(Exception):
                raise laspy.util.LaspyException("Error opening file")

    def get_point_map(self, informat):
        '''Get point map is used to build and return a numpy frombuffer view of the mmapped data, 
        using a valid laspy.util.Format instance for the desired point format. This method is used 
        to provide access to extra_bytes even when dimensions have been explicitly defined via an 
        extra_bytes VLR record.'''
        if type(self._mmap) == bool:
            self.map() 
        self.pointfmt = np.dtype([("point", zip([x.name for x in informat.specs],
                                [x.np_fmt for x in informat.specs]))]) 
        if not self.manager.header.version in ("1.3", "1.4"): 
            _pmap = np.frombuffer(self._mmap, self.pointfmt, 
                        offset = self.manager.header.data_offset)
        else:  
            _pmap = np.frombuffer(self._mmap, self.pointfmt, 
                        offset = self.manager.header.data_offset,
                        count = self.manager.header.point_records_count)
        return(_pmap)


    def point_map(self):
        '''Create the numpy point map based on the point format.'''   
        if type(self._mmap) == bool:
            self.map() 
        self.pointfmt = np.dtype([("point", zip([x.name for x in self.manager.point_format.specs],
                                [x.np_fmt for x in self.manager.point_format.specs]))]) 
        if not self.manager.header.version in ("1.3", "1.4"): 
            self._pmap = np.frombuffer(self._mmap, self.pointfmt, 
                        offset = self.manager.header.data_offset)
            if self.manager.header.point_records_count != len(self._pmap):
                if self.manager.mode == "r":
                    raise laspy.util.LaspyException("""Invalid Point Records Count Information Encountered in Header. 
                                        Please correct. Header.point_records_count = %i, and %i records actually detected."""%(self.manager.header.point_records_count, len(self._pmap)))
                else:
                    print("""WARNING: laspy found invalid data in header.point_records_count. 
                            Header.point_records_count = %i, and %i records actually detected. 
                            Attempting to correct mismatch.""")%(self.manager.header.point_records_count, len(self._pmap))
                    self.manager.header.point_records_count = len(self._pmap)
        else:  
            self._pmap = np.frombuffer(self._mmap, self.pointfmt, 
                        offset = self.manager.header.data_offset,
                        count = self.manager.header.point_records_count)
      

    
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
                    raise laspy.util.LaspyException("Error closing mmap")
        self._mmap = False
        self._pmap = False
        if self.fileref != False:
            try:
                self.fileref.close()
            except(Exception):
                raise laspy.util.LaspyException("Error closing file.")

    def map(self):
        '''Memory map the file'''
        if self.fileref == False and not self.compressed:
            raise laspy.util.LaspyException("File not opened.")
        try:
            if self.mode == "r":
                if self.compressed:
                    self._mmap=FakeMmap(self.filename)
                else:
                    self._mmap = mmap.mmap(self.fileref.fileno(), 0, access = mmap.ACCESS_READ)
            elif self.mode in ("w", "rw"):
                self._mmap = mmap.mmap(self.fileref.fileno(), 0, access = mmap.ACCESS_WRITE)
            else:
                raise laspy.util.LaspyException("Invalid Mode: " + str(self.mode))
        except Exception as e: 
            raise laspy.util.LaspyException("Error mapping file: " + str(e))

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
            raise laspy.util.LaspyException("File not mapped")
        return(self._mmap.size())

class FileManager():
    '''Superclass of Reader and Writer, provides most of the data manipulation functionality in laspy.''' 
    def __init__(self,filename, mode, header = False, vlrs = False, evlrs = False): 
        '''Build the FileManager object. This is done when opening the file
        as well as upon completion of file modification actions like changing the 
        header padding.'''
        self.compressed = False
        self.vlr_formats = laspy.util.Format("VLR")
        self.evlr_formats = laspy.util.Format("EVLR")
        self.mode = mode
        self.data_provider = DataProvider(filename, self) 
        self.setup_memoizing()
        
        self.calc_point_recs = False

        self.point_refs = False
        self._current = 0 
        
        self.padded = False
        if self.mode == "r":
            self.setup_read_write(vlrs,evlrs, read_only=True)
            return
        elif self.mode == "rw":
            self.setup_read_write(vlrs, evlrs, read_only=False)
            return
        elif self.mode == "w":
            self.setup_write(header, vlrs, evlrs)
            return
        else:
            raise laspy.util.LaspyException("Append Mode Not Supported")
        
    def setup_read_write(self, vlrs, evlrs, read_only=True):
        # Check if read only mode, if not open for updating.
        if read_only:
            open_mode = "rb"
        else:
            open_mode = "r+b"
        self._header_current = True
        self.data_provider.open(open_mode)
        self.data_provider.map() 
        self.header_format = laspy.util.Format("h" + self.grab_file_version())
        self.get_header(self.grab_file_version())
        self.populate_vlrs()
        self.point_refs = False
        self.has_point_records = True
        self._current = 0        
        self.correct_rec_len()

        if self.point_format.compressed:
            self.compressed = True
            self.data_provider.remap()
        else:
            self.compressed = False        

        self.data_provider.point_map()
        if self.header.version in ("1.3", "1.4"):
            #gives key error if called with buffer hack for some reason...
            self.populate_evlrs()
        else:
            self.evlrs = []
        if vlrs != False:
            self.set_vlrs(vlrs)
        if evlrs != False:
            self.set_evlrs(vlrs)

        # If extra-bytes descriptions exist in VLRs, use them.
        eb_vlrs = [x for x in self.vlrs if x.type == 1]
        eb_vlrs.extend([x for x in self.evlrs if x.type == 1])
        self.extra_dimensions = []
        if len(eb_vlrs) > 1:
            raise laspy.util.LaspyException("Only one ExtraBytes VLR currently allowed.")
        elif len(eb_vlrs) == 1:
            self.naive_point_format = self.point_format
            self.extra_dimensions = eb_vlrs[0].extra_dimensions
            new_pt_fmt = laspy.util.Format(self.point_format.fmt, extradims 
                    = self.extra_dimensions)
            self.point_format = new_pt_fmt
            self.data_provider.remap(point_map = True)
        return

    def setup_write(self,header, vlrs, evlrs):
        self._header_current = False
        if header == False:
            raise laspy.util.LaspyException("Write mode requires a valid header object.")
        ## No file to store data yet.
        self.has_point_records = False
        self.data_provider.open("w+b") 
        self.header_format = header.format 
        self._header = header
        self.header = laspy.header.HeaderManager(header = header, reader = self)
        self.initialize_file_padding(vlrs)

        ## We have a file to store data now.
        self.data_provider.remap()
        self.header.flush()
        
        self.correct_rec_len()
        if not vlrs in [[], False]:
            self.set_vlrs(vlrs)
        else:
            self.vlrs = []
        if not evlrs in [[], False]:
            self.set_evlrs(evlrs)
        else:
            self.evlrs = []
        self.verify_num_vlrs()
        if self._header.created_year == 0:
            self.header.date = datetime.datetime.now() 
        self.populate_vlrs()
        self.populate_evlrs()
        # If extra-bytes descriptions exist in VLRs, use them.
        eb_vlrs = [x for x in self.vlrs if x.type == 1]
        eb_vlrs.extend([x for x in self.evlrs if x.type == 1])
        self.extra_dimensions = []
        if len(eb_vlrs) > 1:
            raise laspy.util.LaspyException("Only one ExtraBytes VLR currently allowed.")
        elif len(eb_vlrs) == 1:
            self.naive_point_format = self.point_format
            self.extra_dimensions = eb_vlrs[0].extra_dimensions
            new_pt_fmt = laspy.util.Format(self.point_format.fmt, extradims 
                    = self.extra_dimensions)
            self.point_format = new_pt_fmt
        return

    def verify_num_vlrs(self):
        headervlrs = self.get_header_property("num_variable_len_recs")
        calc_headervlrs = len(self.vlrs)
        if headervlrs != calc_headervlrs:
            raise laspy.util.LaspyException('''Number of EVLRs provided does not match the number 
                                 specified in the header. (copied headers do not maintain 
                                 references to their EVLRs, that might be your problem. 
                                 You can pass them explicitly to the File constructor.)''')

        if self.header.version == "1.4":
            calc_headerevlrs = len(self.evlrs)
            headerevlrs = self.get_header_property("num_evlrs")
            if headerevlrs != calc_headerevlrs:
                raise laspy.util.LaspyException('''Number of EVLRs provided does not match the number 
                                     specified in the header. (copied headers do not maintain 
                                     references to their EVLRs, that might be your problem. 
                                     You can pass them explicitly to the File constructor.)''')
    def correct_rec_len(self):
        extrabytes = self.header.data_record_length-laspy.util.Format(self.header.data_format_id).rec_len
        if extrabytes >= 0:
            self.point_format = laspy.util.Format(self.header.data_format_id,extra_bytes= extrabytes)
        else:
            self.point_format = laspy.util.Format(self.header.data_format_id)
            self.set_header_property("data_record_length", self.point_format.rec_len) 

    def initialize_file_padding(self, vlrs):
        filesize = self._header.format.rec_len
        self._header.header_size = filesize
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
            self.c_packers[spec.name] = struct.Struct(spec.fmt)
            self.c_packers[spec.fmt] = self.c_packers[spec.name]

    def packed_str(self, string):
        '''Take a little endian binary string, and convert it to a python int.'''
        return(sum([int(string[idx])*(2**idx) for idx in xrange(len(string))]))

    def binary_str(self, N, zerolen = 8):
        '''Take a python integer and create a binary string padded to len zerolen.'''
        raw_bin = bin(N)[2:][::-1]
        padding = zerolen-len(raw_bin)
        if padding < 0:
            raise laspy.util.LaspyException("Invalid Data: Packed Length is Greater than allowed.")
        return(raw_bin + '0'*(zerolen-len(raw_bin)))
    
    def bit_transform(self, x, low, high):
        return np.right_shift(np.bitwise_and(x, 2**high - 1), low)

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
        
    def read_words(self, name, rec_type = "vlr"):
        '''Read a consecutive sequence of packed binary data, return a single 
        element or list.'''
        if rec_type == "vlr":
            source = self.vlr_formats
        elif rec_type == "evlr":
            source = self.evlr_formats
        elif rec_type == "header":
            source = self.header_format
        else:
            raise laspy.util.LaspyException("Invalid source: " + str(rec_type))
        try:
            dim = source.lookup[name]
        except KeyError:
            raise laspy.util.LaspyException("Dimension " + name + " not found.")       
        return(self._read_words(dim.fmt, dim.num, dim.length))

    def _read_words(self, fmt, num, bytes):
        '''Read a consecutive sequence of packed binary data, return a single
        element or list''' 
        outData = []
        for i in xrange(num):
            dat = self.read(bytes)
            outData.append(struct.unpack(fmt, dat)[0])
        if len(outData) > 1:
            return(outData)
        return(outData[0])
    
    def _pack_words(self, fmt, num, bytes, val):
        if num == 1:
            return(struct.pack(fmt, val))
        outData = "".join([struct.pack(fmt, val[i]) for i in xrange(num)])
        return(outData)


    def grab_file_version(self):
        '''Manually grab file version from header'''
        self.seek(24, rel = False)
        v1 = self._read_words("<B", 1, 1)
        v2 = self._read_words("<B", 1, 1)
        self.seek(0, rel = False)
        return(str(v1) +"." +  str(v2))

    def get_header(self, file_version = 1.2):
        '''Return the header object, or create one if absent.'''
        ## Why is this != neccesary?
        try:
            return(self.header)
        except: 
            self.header = laspy.header.HeaderManager(header = laspy.header.Header(file_version), reader = self)
            return(self.header)

    def populate_evlrs(self): 
        '''Catalogue the extended variable length records'''
        self.evlrs = []
      
        if not self.header.version in ("1.3", "1.4"):
            return
        
       
        if self.header.version == "1.3":
            if self.header.start_wavefm_data_rec != 0:
                self.seek(self.header.start_wavefm_data_rec, rel = False)
                num_vlrs = 1
            else:
                num_vlrs = 0
        elif self.header.version == "1.4":
            self.seek(self.header.start_first_evlr, rel = False)
            num_vlrs = self.get_header_property("num_evlrs")
        for i in xrange(num_vlrs): 
            new_vlr = laspy.header.EVLR(None, None, None)
            new_vlr.build_from_reader(self)
            self.evlrs.append(new_vlr)  
        return


    def populate_vlrs(self): 
        '''Catalogue the variable length records'''
        self.vlrs = []
        self.seek(self.header.header_size, rel = False)
        for i in xrange(self.get_header_property("num_variable_len_recs")): 
            new_vlr = laspy.header.VLR(None, None, None)
            new_vlr.build_from_reader(self)
            self.vlrs.append(new_vlr)
            if self.data_provider._mmap.tell() > self.header.data_offset:
                self.seek(self.header.data_offset, rel = False)
                raise laspy.util.LaspyException("Error, Calculated Header Data "
                    "Overlaps The Point Records!")
        self.vlr_stop = self.data_provider._mmap.tell()
        return

    def get_vlrs(self):
        '''Populate and return list of :obj:`laspy.header.VLR` objects`.'''
        try:
            return(self.vlrs)
        except:
            self.populate_vlrs()
            return(self.vlrs)
    
    def push_vlrs(self):
        self.set_vlrs(self.vlrs)

    def get_evlrs(self):
        try:
            return(self.evlrs)
        except:
            self.populate_evlrs()
            return(self.evlrs)

    def get_padding(self):
        '''Return the padding between the end of the VLRs and the beginning of
        the point records'''
        return(self.header.data_offset - self.vlr_stop)

    def get_pointrecordscount(self):
        '''calculate the number of point records'''
        return(self.get_header_property("point_records_count"))

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
        #return((laspy.util.Point(self, unpacked_list = pts[fmtlen*i:fmtlen*(i+1)]) for i in xrange(self.header.point_records_count)))
        #return([laspy.util.Point(self,x) for x in self._get_raw_dimension(0, self.header.data_record_length)])
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
        return(laspy.util.Point(self, self.get_raw_point(index), nice= nice))

    
    def get_next_point(self):
        '''Return next point object via get_point / #legacy_api'''
        if self._current == None:
            raise laspy.util.LaspyException("No Current Point Specified," + 
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
            raise laspy.util.LaspyException("Dimension: " + str(name) + 
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
            return(struct.unpack(spec.fmt, data)[0])
        unpacked = map(lambda x: struct.unpack(spec.fmt, 
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
        #print name
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
   
    def get_raw_classification_flags(self):
        return(self.get_dimension("classification_flags"))

    def get_classification_flags(self): 
        if not self.header.data_format_id in (6,7,8,9,10):
            return(self.get_classification())
        rawDim = self.get_raw_classification_flags()
        return self.bit_transform(rawDim, 0, 4)

    def get_classification_byte(self):
        return(self.get_dimension("classification_byte"))

    def get_return_num(self):
        rawDim = self.get_flag_byte()
        if self.header.data_format_id in (0,1,2,3,4,5):
            return self.bit_transform(rawDim, 0, 3)
        elif self.header.data_format_id in (6,7,8,9,10):
            return self.bit_transform(rawDim, 0, 4)

    def get_num_returns(self):
        rawDim = self.get_flag_byte()
        if self.header.data_format_id in (0,1,2,3,4,5):
            return self.bit_transform(rawDim, 3, 6)
        elif self.header.data_format_id in (6,7,8,9,10):
            return self.bit_transform(rawDim, 4, 8)

    def get_scanner_channel(self):
        rawDim = self.get_raw_classification_flags()
        if not self.header.data_format_id in (6,7,8,9,10):
            raise laspy.util.LaspyException("Scanner Channel not present for point format: " + str(self.header.data_format_id))
        return self.bit_transform(rawDim, 4, 6)

    def get_scan_dir_flag(self):
        if self.header.data_format_id in (0,1,2,3,4,5):
            rawDim = self.get_flag_byte()
        elif self.header.data_format_id in (6,7,8,9,10):
            rawDim = self.get_raw_classification_flags()
        return self.bit_transform(rawDim, 6, 7)

    def get_edge_flight_line(self): 
        if self.header.data_format_id in (0,1,2,3,4,5):
            rawDim = self.get_flag_byte() 
        elif self.header.data_format_id in (6,7,8,9,10):
            rawDim = self.get_raw_classification_flags() 
        return self.bit_transform(rawDim, 7, 8)
    
    def get_raw_classification(self):
        return(self.get_dimension("raw_classification"))
    
    def get_classification(self): 
        if self.header.data_format_id in (0,1,2,3,4,5):
            return self.bit_transform(self.get_raw_classification(), 0, 5)
        elif self.header.data_format_id in (6,7,8,9,10):
            return(self.get_dimension("classification_byte"))

    def get_synthetic(self):
        if self.header.data_format_id in (6,7,8,9,10):
            return self.bit_transform(self.get_raw_classification_flags(), 0, 1)

        return self.bit_transform(self.get_raw_classification(), 5, 6)

    def get_key_point(self):
        if self.header.data_format_id in (6,7,8,9,10):
            return self.bit_transform(self.get_raw_classification_flags(), 1, 2)

        return self.bit_transform(self.get_raw_classification(), 6, 7)

    def get_withheld(self):
        if self.header.data_format_id in (6,7,8,9,10):
            return self.bit_transform(self.get_raw_classification_flags(), 2, 3)

        return self.bit_transform(self.get_raw_classification(), 7, 8)
    
    def get_overlap(self):
        if self.header.data_format_id in (6,7,8,9,10):
            return self.bit_transform(self.get_raw_classification_flags(), 3, 4)
        else:
            raise laspy.util.LaspyException("Overlap only present in point formats > 5.")

    def get_scan_angle_rank(self):
        return(self.get_dimension("scan_angle_rank"))
    
    def get_user_data(self):
        return(self.get_dimension("user_data"))
    
    def get_pt_src_id(self):
        return(self.get_dimension("pt_src_id"))
    
    def get_gps_time(self):
        return(self.get_dimension("gps_time"))

    def get_red(self):
        return(self.get_dimension("red"))
    
    def get_green(self):
        return(self.get_dimension("green"))
 
    def get_blue(self):
        return(self.get_dimension("blue"))


    def get_nir(self):
        return(self.get_dimension("nir"))


    def get_wave_packet_desc_index(self):
        return(self.get_dimension("wave_packet_desc_index"))

    def get_byte_offset_to_waveform_data(self):
        return(self.get_dimension("byte_offset_to_waveform_data"))

    def get_waveform_packet_size(self):
        return(self.get_dimension("waveform_packet_size"))

    def get_return_point_waveform_loc(self):
        return(self.get_dimension("return_point_waveform_loc"))

    def get_x_t(self):
        return(self.get_dimension("x_t"))

    def get_y_t(self):
        return(self.get_dimension("y_t"))

    def get_z_t(self):
        return(self.get_dimension("z_t"))

    def get_extra_bytes(self):
        if "extra_bytes" in self.point_format.lookup.keys():
            return(self.get_dimension("extra_bytes"))
        elif self.extra_dimensions != []:
            newmap = self.data_provider.get_point_map(self.naive_point_format) 
            return(newmap["point"]["extra_bytes"])
        else:
            raise laspy.util.LaspyException("Extra bytes not present in record")


class Reader(FileManager):
    def close(self):
        '''Close the file.'''
        self.data_provider.close() 
    
class Writer(FileManager):

    def close(self, ignore_header_changes = False, minmax_mode = "scaled"):
        '''Flush changes to mmap and close mmap and fileref''' 
        if (not ignore_header_changes) and (self.has_point_records):
            if not self._header_current:
                self.header.update_histogram()
            self.header.update_min_max(minmax_mode) 
        self.data_provider.close()
   
    def set_evlrs(self, value):
        if value == False or len(value) == 0:
            return
        if not all([x.isEVLR for x in value]):
            raise laspy.util.LaspyException("set_evlrs requers an iterable object " + 
                        "composed of :obj:`laspy.header.EVLR` objects.")
        elif self.mode == "w+":
            raise NotImplementedError
        elif self.mode in ("rw", "w"): 
            if self.header.version == "1.3":
                old_offset = self.header.start_wavefm_data_rec
            elif self.header.version == "1.4":
                old_offset = self.header.start_first_evlr
                self.set_header_property("num_evlrs", len(value))
            else:
                raise laspy.util.LaspyException("Invalid File Version for EVLRs: " + str(self.header.version))
            # Good we know where the EVLRs should go... but what about if we don't have point records yet?
            # We can't make that decision yet, in case the user wants to subset the data. 
            if not self.has_point_records:
                old_offset = self.header.data_offset
                if self.header.version == "1.3":
                    self.header.start_wavefm_data_rec = old_offset
                else:
                    if len(value) == 1:
                        self.header.start_first_evlr = old_offset
                        self.header.start_wavefm_data_rec = old_offset
                    else:
                        wf = self.header.start_wavefm_data_rec
                        fe = self.header.start_first_evlr
                        new_wvfm = wf - min(wf, fe) + old_offset
                        new_frst = fe - min(wf, fe) + old_offset
                        self.header.start_wavefm_data_rec = new_wvfm
                        self.header.start_first_evlr = new_frst
                #if old_offset != 0:
                #    self.pad_file_for_point_recs(self.get_pointrecordscount())
                #else:
                #    old_offset = self.header.data_offset
                #    self.pad_file_for_point_recs(self.get_pointrecordscount())

            self.data_provider.fileref.seek(0, 0)
            dat_part_1 = self.data_provider.fileref.read(old_offset)
            # Manually Close:
            self.data_provider.close(flush=False)
            self.data_provider.open("w+b")
            self.data_provider.fileref.write(dat_part_1)
            total_evlrs = sum([len(x) for x in value])
            self.data_provider.fileref.write("\x00"*total_evlrs) 
            self.data_provider.fileref.close()
            self.data_provider.open("r+b")
            self.data_provider.map()
            self.seek(old_offset, rel = False)

            for evlr in value: 
                self.data_provider._mmap.write(evlr.to_byte_string())

            if self.has_point_records:
                self.data_provider.point_map()
            self.populate_evlrs()

        else:
            raise(laspy.util.LaspyException("set_evlrs requires the file to be opened in a " + 
                "write mode, and must be performed before point information is provided." + 
                "Try closing the file and opening it in rw mode. "))
 
    def save_vlrs(self):
        self.set_vlrs(self.vlrs)

    def set_vlrs(self, value): 
        if value == False or len(value) == 0:
            return
        if not all([x.isVLR for x in value]):
            raise laspy.util.LaspyException("set_vlrs requers an iterable object " + 
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
            self.populate_vlrs()
        elif self.mode == "w" and not self.has_point_records: 

            self.set_header_property("num_variable_len_recs", len(value))
            if (self.data_provider._mmap.size() < self.header.header_size + sum([len(x) for x in value])): 
                old_offset = self.header.header_size
                self.data_provider.fileref.seek(0, 0)
                dat_part_1 = self.data_provider.fileref.read(self.header.header_size) 
                # Manually Close:
                self.data_provider.close(flush=False)
                self.data_provider.open("w+b")
                self.data_provider.fileref.write(dat_part_1)
                for vlr in value:
                    byte_string = vlr.to_byte_string()
                    self.data_provider.fileref.write(byte_string)

                self.data_provider.fileref.close()
                self.data_provider.open("r+b")

                self.data_provider.remap()
                new_offset = self.header.header_size + sum([len(x) for x in value])
                self.set_header_property("data_offset", new_offset)

            self.seek(self.header.header_size, rel = False)
            for vlr in value:
                self.data_provider._mmap.write(vlr.to_byte_string())
            self.populate_vlrs()
            return
        else:
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
            self.populate_vlrs() 


    def set_padding(self, value):
        '''Set the padding between end of VLRs and beginning of point data'''
        if value < 0: 
            raise laspy.util.LaspyException("New Padding Value Overwrites VLRs")
        if self.mode == "w":
            if not self.has_point_records:
                self.data_provider.fileref.seek(self.vlr_stop, 0)
                self.data_provider.fileref.write("\x00"*value)
                self.data_provider.remap()
                return
            else:
                raise laspy.util.LaspyException("Laspy does not yet support assignment of EVLRs for files which already contain point records.")
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
            raise(laspy.util.LaspyException("Must be in write mode to change padding."))
        return(len(self.data_provider._mmap))
    
    def pad_file_for_point_recs(self,num_recs): 
        '''Pad the file with null bytes out to a calculated length based on 
        the data given. This is usually a side effect of set_dimension being 
        called for the first time on a file in write mode. '''

        bytes_to_pad = num_recs * self.point_format.rec_len
        self.header.point_records_count = num_recs
        if self.evlrs in [False, []]:
            #old_size = self.data_provider.filesize()
            old_size = self.header.data_offset     
            self.data_provider._mmap.flush()
            self.data_provider.fileref.seek(old_size, 0)
            self.data_provider.fileref.write("\x00" * (bytes_to_pad))
            self.data_provider.fileref.flush()
            self.data_provider.remap(flush = False, point_map = True) 
            # Write Phase complete, enter rw mode?
            self.padded = num_recs
            return
        else:
            d1 = self.data_provider._mmap[0:self.header.data_offset]
            d2 = self.data_provider._mmap[self.header.data_offset:self.data_provider._mmap.size()]
            self.data_provider.close()
            self.data_provider.open("w+b")
            self.data_provider.fileref.write(d1)
            self.data_provider.fileref.write("\x00"*(bytes_to_pad))
            self.data_provider.fileref.write(d2)
            self.data_provider.close()
            self.data_provider.remap(point_map = True)
            self.header.start_wavefm_data_rec += bytes_to_pad
            if self.header.version == "1.4":
                self.header.start_first_evlr += bytes_to_pad
        
    def define_new_dimension(self,name, data_type,description = ""):
        old_vlrs = self.vlrs
        if self.has_point_records or not self.mode == "w":
            raise laspy.util.LaspyException("New dimensions may be defined only for write mode files which do not yet possess point records.")
        eb_vlrs = [x for x in self.vlrs if x.type == 1]
        if self.header.version == "1.4":
            eb_evlrs =  [x for x in self.evlrs if x.type == 1]
            old_evlrs = self.evlrs
        else:
            eb_evlrs = []
            old_evlrs = []

        if ("extra_bytes" in self.point_format.lookup) and (len(eb_vlrs) != 0):
            raise laspy.util.LaspyException("Adding a dimension is ambiguous when there are already extra bytes in the point records, but no VLR describing them.")
        new_dimension = laspy.header.ExtraBytesStruct(name = name, data_type = data_type, description = description)
        if len(eb_vlrs) + len(eb_evlrs) > 1:
            raise laspy.util.LaspyException("Only one ExtraBytes VLR currently allowed.") 
        elif len(eb_vlrs) + len(eb_evlrs) == 1:
            if len(eb_vlrs) == 1:
                extra_dimensions = eb_vlrs[0].extra_dimensions
                extra_dimensions.append(new_dimension)
                self.extra_dimensions = extra_dimensions
                new_pt_fmt = laspy.util.Format(self.point_format.fmt, extradims 
                             = extra_dimensions)
                self.point_format = new_pt_fmt
                self.set_header_property("data_record_length", self.point_format.rec_len)

                eb_vlr_index = [x for x in range(len(self.vlrs)) if self.vlrs[x].type == 1][0]
                new_vlr = copy.copy(eb_vlrs[0])
                nvlrbs = new_dimension.to_byte_string()
                new_vlr.VLR_body += nvlrbs 
                new_vlr.rec_len_after_header += len(nvlrbs)
                old_vlrs[eb_vlr_index] = new_vlr 
                self.set_vlrs(old_vlrs)
                self.populate_vlrs()
            elif len(eb_evlrs) == 1:
                extra_dimensions = eb_evlrs[0].extra_dimensions
                extra_dimensions.append(new_dimension)
                self.extra_dimensions = extra_dimensions
                new_pt_fmt = laspy.util.Format(self.point_format.fmt, extradims 
                             = extra_dimensions)
                self.point_format = new_pt_fmt
                self.set_header_property("data_record_length", self.point_format.rec_len)
                eb_evlr_index = [x for x in range(len(self.evlrs)) if self.evlrs[x].type == 1][0]
                new_vlr = copy.copy(eb_evlrs[0])
                nvlrbs = new_dimension.to_byte_string()
                new_vlr.VLR_body += nvlrbs 
                new_vlr.rec_len_after_header += len(nvlrbs)
                old_vlrs[eb_evlr_index] = new_vlr 
                self.set_evlrs(old_evlrs)
                self.populate_evlrs()
        else:
            # There are no current extra dimensions.
            new_vlr = laspy.header.VLR(user_id = "LASF_Spec", record_id = 4, VLR_body = new_dimension.to_byte_string())
            old_vlrs.append(new_vlr) 
            self.extra_dimensions = [new_dimension]
            
            new_pt_fmt = laspy.util.Format(self.point_format.fmt, extradims = self.extra_dimensions)
            self.point_format = new_pt_fmt
            self.set_header_property("data_record_length", self.point_format.rec_len)
            self.set_vlrs(old_vlrs)
            self.populate_vlrs()

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
            raise laspy.util.LaspyException("Error, new dimension length (%s) does not match"%str(len(new_dim)) + " the number of points (%s)" % str(ptrecs))
        try:
            spec = self.point_format.lookup[name]
            return(self._set_dimension(spec, new_dim))
        except KeyError:
            raise laspy.util.LaspyException("Dimension: " + str(name) + 
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
        if isinstance(points[0], laspy.util.Point):
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
            raise laspy.util.LaspyException("Error, new dimension length (%s) does not match"%str(len(new_raw_points)) + " the number of points (%s)" % str(ptrecs)) 
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
                self.data_provider._mmap[lb:ub] = struct.pack(dim.fmt, val)
            except:
                self.data_provider._mmap[lb:ub] = struct.pack(dim.fmt, int(val))

            return

        try:
            dimlen = len(val)
        except(Exception):
            dimlen = 1

        if dim.num != dimlen:
            raise(laspy.util.LaspyException("Fields must be replaced with data of the same length. " + 
                                str(dim.name) +" should be length " + 
                                str(dim.num) +", received " + str(dimlen) ))
        def f(x):
            try:
                outbyte = struct.pack(dim.fmt, val[x])
            except:
                outbyte = struct.pack(dim.fmt, int(val[x]))
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
            raise(laspy.util.LaspyException("Header Dimension: " + 
                  str(name) + " not found."))
        self._set_raw_datum(0, spec, value)

    def set_header_property(self, name, value):
        '''Wrapper for _set_datum, accepting name of header property and formatted value'''
        try:
            dim = self.header_format.lookup[name]
        except(KeyError):
            raise laspy.util.LaspyException("Header Dimension: " + str(name) + " not found.")
        if not dim.overwritable:
            raise(laspy.util.LaspyException("Field " + dim.name + " is not overwritable."))
        
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
    
    def bitpack(self, arrs, indices):
        '''Pack an array of integers into a byte based on idx
        for example bitpack((arr1, arr2), (0,3), (3,8)) packs the integers
        arr1 and arr2 into a byte, using the first three bits
        of arr1, and the last five bits of arr2. 
        '''
        def keep_bits(arr, low, high):
            """ Keep only the bits on the interval [low, high) """
            return np.bitwise_and(np.bitwise_and(arr, 2**high - 1),
                                  ~(2**low - 1)).astype(np.uint8)

        first_bit_idx = 0 # Stack the bits from the beginning

        packed = np.zeros_like(arrs[0])
        for arr, (low, high) in zip(arrs, indices):
            if low > first_bit_idx:
                packed += np.right_shift(keep_bits(arr, low, high), 
                                         low - first_bit_idx)
            else:
                packed += np.left_shift(keep_bits(arr, low, high), 
                                        first_bit_idx - low)

            # First bit index should never be > 8 if we are 
            # packing values to a byte
            first_bit_idx += high - low

            if first_bit_idx > 8:
                raise laspy.util.LaspyException("Invalid Data: Packed Length is Greater than allowed.")

        return list(packed)

    def raise_if_overflow(self, arr, maximum_packed_length):
        if np.any(np.array(arr) >= 2**maximum_packed_length):
            raise laspy.util.LaspyException("Invalid Data: Packed Length is Greater than allowed.")


    def set_return_num(self, num):
        '''Set the binary field return_num in the flag_byte''' 
        self._header_current = False
        if self.header.data_format_id in (0,1,2,3,4,5):
            flag_byte = self.get_flag_byte()
            self.raise_if_overflow(num, 3)
            outByte = self.bitpack((num,flag_byte), ((0,3), (3,8)))
            self.set_dimension("flag_byte", outByte)
        elif self.header.data_format_id in (6,7,8,9,10):
            flag_byte = self.get_flag_byte()
            self.raise_if_overflow(num, 4)
            outByte = self.bitpack((num,flag_byte), ((0,4), (4,8)))
            self.set_dimension("flag_byte", outByte)
        return

    def set_num_returns(self, num):
        '''Set the binary field num_returns in the flag_byte'''
        self._header_current = False
        if self.header.data_format_id in (0,1,2,3,4,5):
            flag_byte = self.get_flag_byte()
            self.raise_if_overflow(num, 3)
            outByte = self.bitpack((flag_byte, num,flag_byte), ((0,3),(0,3),(6,8)))
            self.set_dimension("flag_byte", outByte)
        elif self.header.data_format_id in (6,7,8,9,10):
            flag_byte = self.get_flag_byte()
            self.raise_if_overflow(num, 4)
            outByte = self.bitpack((flag_byte, num), ((0,4), (4,8)))
            self.set_dimension("flag_byte", outByte)
        return

    def set_scanner_channel(self, value): 
        if not self.header.data_format_id in (6,7,8,9,10):
            raise laspy.util.LaspyException("Scanner Channel not present for point format: " + str(self.header.data_format_id))
        raw_dim = self.get_raw_classification_flags()
        self.raise_if_overflow(value, 2)
        outByte = self.bitpack((raw_dim, value, raw_dim), ((0,4), (0,2), (6,8)))
        self.set_raw_classification_flags(outByte) 

    def set_scan_dir_flag(self, flag): 
        '''Set the binary field scan_dir_flag in the flag_byte'''
        if self.header.data_format_id in (0,1,2,3,4,5):
            flag_byte = self.get_flag_byte()
            self.raise_if_overflow(flag, 1)
            outByte = self.bitpack((flag_byte,flag,flag_byte), 
                ((0,6),(0,1), (7,8)))
            self.set_dimension("flag_byte", outByte)
        elif self.header.data_format_id in (6,7,8,9,10):
            flag_byte = self.get_raw_classification_flags()
            self.raise_if_overflow(flag, 1)
            outByte = self.bitpack((flag_byte,flag,flag_byte), 
                ((0,6),(0,1), (7,8)))
            self.set_dimension("classification_flags", outByte)
        return

    def set_edge_flight_line(self, line):
        '''Set the binary field edge_flight_line in the flag_byte'''
        if self.header.data_format_id in (0,1,2,3,4,5):
            raw_dim = self.get_flag_byte()
            self.raise_if_overflow(line, 1)
            outByte = self.bitpack((raw_dim, line), ((0,7), (0,1)))
            self.set_dimension("flag_byte", outByte)
        elif self.header.data_format_id in (6,7,8,9,10):
            raw_dim = self.get_raw_classification_flags()
            self.raise_if_overflow(line, 1)
            outByte = self.bitpack((raw_dim, line), ((0,7), (0,1)))
            self.set_dimension("classification_flags", outByte)
        return

    def set_classification_byte(self, value):
        self.set_dimension("classification_byte", value)

    def set_raw_classification_flags(self, value):
        self.set_dimension("classification_flags",value)
    
    def set_classification_flags(self, value): 
        if not self.header.data_format_id in (6,7,8,9,10):
            self.set_classification(value)
            return
        rawDim = self.get_raw_classification_flags()
        self.raise_if_overflow(value, 4)
        outbyte = self.bitpack((value, rawDim), ((0,4), (4,8)))
        self.set_raw_classification_flags(outbyte)
        return

    def set_raw_classification(self, classification):
        '''Set the entire classification byte at once. This is faster than setting the binary fields individually, 
        but care must be taken that the values mean what you think they do. '''
        self.set_dimension("raw_classification", classification)

    def set_classification(self, classification):
        '''Point Formats <6: Set the binary classification field inside the raw classification byte
           Point Formats >5: Set the classification byte.
        '''
        if self.header.data_format_id in (0,1,2,3,4,5):
            class_byte = self.get_raw_classification()
            self.raise_if_overflow(classification, 5)
            out_byte = self.bitpack((classification, class_byte), ((0,5), (5,8)))
            self.set_raw_classification(out_byte)
        elif self.header.data_format_id in (6,7,8,9,10):
            self.set_dimension("classification_byte", classification)
        return

    def set_synthetic(self, synthetic):
        '''Set the binary field synthetic inside the raw classification byte'''
        if self.header.data_format_id in (6,7,8,9,10):
            class_byte = self.get_raw_classification_flags()
            self.raise_if_overflow(synthetic, 1)
            out_byte = self.bitpack((synthetic, class_byte), 
                                    ((0,1), (1,8)))
            self.set_raw_classification_flags(out_byte)
        else:
            class_byte = self.get_raw_classification()
            self.raise_if_overflow(synthetic, 1)
            out_byte = self.bitpack((class_byte, synthetic, class_byte),
                                   ((0,5), (0,1), (6,8)))
            self.set_dimension("raw_classification", out_byte)
        return

    def set_key_point(self, pt):
        '''Set the binary key_point field inside the raw classification byte'''
        if self.header.data_format_id in (6,7,8,9,10):
            class_byte = self.get_raw_classification_flags()
            self.raise_if_overflow(pt, 1)
            outbyte = self.bitpack((class_byte, pt, class_byte), ((0,1),(0,1), (2,8)))
            self.set_raw_classification_flags(outbyte)
        else:
            class_byte = self.get_raw_classification()
            self.raise_if_overflow(pt, 1)
            out_byte = self.bitpack((class_byte, pt, class_byte), 
                                ((0,6),(0,1),(7,8)))
            self.set_dimension("raw_classification", out_byte)
        return
 
    def set_withheld(self, withheld):
        '''Set the binary field withheld inside the raw classification byte'''
        if self.header.data_format_id in (6,7,8,9,10):
            class_byte = self.get_raw_classification_flags()
            self.raise_if_overflow(withheld, 1)
            outbyte = self.bitpack((class_byte, withheld, class_byte), ((0,2),(0,1), (3,8)))
            self.set_raw_classification_flags(outbyte)
        else:
            class_byte = self.get_raw_classification()
            self.raise_if_overflow(withheld, 1)
            out_byte = self.bitpack((class_byte, withheld),
                                 ((0,7), (0,1)))
            self.set_dimension("raw_classification", out_byte)
        return

    def set_overlap(self, overlap):
        '''Set the binary field withheld inside the raw classification byte'''
        if self.header.data_format_id in (6,7,8,9,10):
            class_byte = self.get_raw_classification_flags()
            self.raise_if_overflow(overlap, 1)
            outbyte = self.bitpack((class_byte, overlap, class_byte), ((0,3),(0,1), (4,8)))
            self.set_raw_classification_flags(outbyte)
        else:
            raise laspy.util.LaspyException("Overlap only present in point formats > 5.")
        return


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
        self.set_dimension("gps_time", data)
    
    def set_red(self, red):
        '''Wrapper for set_dimension("red")'''
        self.set_dimension("red", red)

    def set_green(self, green):
        '''Wrapper for set_dimension("green")'''
        self.set_dimension("green", green) 
    
    def set_blue(self, blue):
        '''Wrapper for set_dimension("blue")'''
        self.set_dimension("blue", blue)

    def set_nir(self, value):
        self.get_dimension("nir", value)

    def set_wave_packet_desc_index(self, idx):
        '''Wrapper for set_dimension("wave_packet_desc_index") This is not currently functional, 
        since addition of waveform data broke the numpy point map.'''
        self.set_dimension("wave_packet_desc_index", idx)

    def set_byte_offset_to_waveform_data(self, idx):
        '''Wrapper for set_dimension("byte_offset_to_waveform_data"), not currently functional,
        because addition of waveform data broke the numpy point map.'''
        self.set_dimension("byte_offset_to_waveform_data", idx)
    
    def set_waveform_packet_size(self, size):
        '''Wrapper for set_dimension("waveform_packet_size"), not currently functional, because
        addition of waveform data broke the numpy point map.'''
        self.set_dimension("waveform_packet_size", size)
    
    def set_return_point_waveform_loc(self, loc):
        '''Wrapper for set_dimension("return_point_waveform_loc"), not currently functional,
        because addition of waveform data broke the numpy point map.'''
        self.set_dimension("return_point_waveform_loc", loc)
    
    def set_x_t(self, x):
        '''Wrapper for set_dimension("x_t")'''
        self.set_dimension("x_t", x)

    def set_y_t(self, y):
        '''Wrapper for set_dimension("y_t")'''
        self.set_dimension("y_t", y)
    
    def set_z_t(self, z):
        '''Wrapper for set_dimension("z_t")'''
        self.set_dimension("z_t", z)

    def set_extra_bytes(self, extra_bytes):
        '''Wrapper for set_dimension("extra_bytes")'''
        if "extra_bytes" in self.point_format.lookup.keys():
            self.set_dimension("extra_bytes", extra_bytes)
        elif self.extra_dimensions != []:
            newmap = self.data_provider.get_point_map(self.naive_point_format) 
            newmap["point"]["extra_bytes"] = extra_bytes
        else:
            raise laspy.util.LaspyException("Extra bytes not present in point format. Try creating a new file with an extended point record length.")

