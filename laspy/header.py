import datetime
import uuid
import util
import struct
import copy
import numpy as np

def leap_year(year):
    if ((year % 4) != 0):
        return False
    elif ((year % 100) != 0):
        return True
    elif ((year % 400) != 0):
        return False
    return True

## NOTE: set_attr methods are currently not implemented. These methods need
## to update the file using reader/mmap. 
class LaspyHeaderException(Exception):
    pass


class ParseableVLR():
    def parse_data(self):
        '''Attempt to read VLR or EVLR body into the parsed_body attribute.'''
 
        if "LASF_Projection" in self.user_id and self.record_id == 2111:
            # OGC Math Transform WKT Record
            self.body_fmt = util.Format(None)
            self.body_fmt.add("ogc_math_transform", "ctypes.c_char", self.rec_len_after_header)

        elif "LASF_Projection" in self.user_id and self.record_id == 2112:
            # OGC Coordinate System WKT
            self.body_fmt = util.Format(None)
            self.body_fmt.add("coordinate_system_wkt", "ctypes.c_char", self.rec_len_after_header)

        elif "LASF_Projection" in self.user_id and self.record_id == 34735:
            # GeoKeyDictionaryTag Record
            self.body_fmt = util.Format(None)
            self.body_fmt.add("wKeyDirectoryVersion", "ctypes.c_ushort", 1)
            self.body_fmt.add("wKeyRevision", "ctypes.c_ushort", 1)
            self.body_fmt.add("wMinorRevision", "ctypes.c_ushort", 1)
            self.body_fmt.add("wNumberOfKeys", "ctypes.c_ushort", 1)   
            # Rest is made up of arrays of 4 unsigned shorts. 
            bytes_left = (self.rec_len_after_header - 4*2)
            if bytes_left % (4*2) != 0:
                print("WARNING: Invalid body length for GeoKeyDictionaryTag, Not parsing.")
                self.body_fmt = None
                return
            for sKeyEntry in xrange(bytes_left/8):
                self.body_fmt.add("wKeyId_%i" % sKeyEntry, "ctypes.c_ushort", 1)
                self.body_fmt.add("wTIFFTagLocation_%i" % sKeyEntry, "ctypes.c_ushort", 1)
                self.body_fmt.add("wCount_%i" % sKeyEntry, "ctypes.c_ushort", 1)
                self.body_fmt.add("wValue_Offset_%i" % sKeyEntry, "ctypes.c_ushort", 1)

        elif "LASF_Projection" in self.user_id and self.record_id == 34736:
            # Geo Double Params Tag Record
            self.body_fmt = util.Format(None)
            if self.rec_len_after_header % 8 != 0:
                print("WARNING: Invalid body length for GeoDoubleParamsTag, not parsing.")
                return
            for i in xrange(self.rec_len_after_header/8):
                self.body_fmt.add("param_%i" % i, "ctypes.c_double", 1)

        elif "LASF_Projection" in self.user_id and self.record_id == 34737:
            # GeoAsciiParamsTagRecord
            self.body_fmt = util.Format(None)
            self.body_fmt.add("GeoASCIIParamsTag", "ctypes.c_char", self.rec_len_after_header)

        elif "LASF_Spec" in self.user_id and self.record_id == 0:            
            # Classification Lookup
            self.body_fmt = util.Format(None)
            if self.rec_len_after_header % 16 != 0:
                print("WARNING: Invalid body length for classification lookup, not parsing.")
                return
            for i in xrange(self.rec_len_after_header / 16):
                self.body_fmt.add("ClassNumber_%i", "ctypes.c_ubyte", 1)
                self.body_fmt.add("Description_%i", "ctypes.c_char", 15)

        elif "LASF_Spec" in self.user_id and self.record_id == 1:            
            # Header Flight line lookup
            self.body_fmt = util.Format(None)
            if self.rec_len_after_header % 257 != 0:
                print("WARNING: Invalid body length for header flight line lookup, not parsing.")
                return
            for i in xrange(self.rec_len_after_header / 257):
                self.body_fmt.add("FileMarkerNumber_%i", "ctypes.c_ubyte", 1)
                self.body_fmt.add("Filename_%i", "ctypes.c_char", 256)

        elif "LASF_Spec" in self.user_id and self.record_id == 3:            
            #Text Area Description
            self.body_fmt = util.Format(None)
            self.body_fmt.add("text_area_description", "ctypes.c_char", self.rec_len_after_header)

        elif "LASF_Spec" in self.user_id and self.record_id == 4:            
            # Extra Bytes, currently handled by VLR constructor
            pass

        elif "LASF_Spec" in self.user_id and self.record_id > 99 and self.record_id < 355:
            # WAVEFORM PACKET DESCRIPTOR
            self.body_fmt = util.Format(None)
            self.body_fmt.add("bits_per_sample", "ctypes.c_ubyte",1)
            self.body_fmt.add("waveform_compression_type", "ctypes.c_ubyte",1)
            self.body_fmt.add("number_of_samples", "ctypes.c_ulong",1)
            self.body_fmt.add("temporal_time_spacing", "ctypes.c_ulong",1)
            self.body_fmt.add("digitizer_gain", "ctypes.c_double",1)
            self.body_fmt.add("digitizer_offset", "ctypes.c_double",1)

        if self.body_fmt != None:
            self.parsed_body = np.array(struct.unpack(self.body_fmt.pt_fmt_long, self.VLR_body))
        else:
            self.parsed_body = None
    
    def pack_data(self):
        '''Pack data from parsed_body into VLR_body.'''
        if self.body_fmt == None:
            raise util.LaspyException("Not a known VLR/EVLR type, can't pack parsed_body")
        try:
            packed = struct.pack(self.body_fmt.pt_fmt_long, *self.parsed_body)
        except Exception, error:    
            print("Error packing VLR data, using current raw vlr body.")
            print(error)
            packed = self.VLR_body
        self.VLR_body = packed

    def body_summary(self):
        '''Print a summary of parsed_body to the log.'''
        if self.body_fmt == None:
            return
        idx = 0
        for i in self.body_fmt:
            out = str(self.parsed_body[idx])
            print(i.name + ": " + (20-len(i.name))*" "  + out)
            idx += 1

class ExtraBytesStruct(object):
    '''This class provides a frontend for the Extra Bytes Struct as defined
    in the LAS 1.4 specification. All Arguments are assumed to be default values
    unless specified - the two really key ones are name and data_type. This structure
    lives in the VLR_body property of a laspy.header.VLR instance, and multiple 
    ExtraByteStruct records can be present together. Each ExtraBytesStruct instance
    describes an additional dimension present at the end of each point record. ''' 
    def __init__(self, data_type = 0, options = 0, name = "\x00"*32, 
                 unused = [0]*4, no_data = [0.0]*3, min = [0.0]*3, 
                 max = [0.0]*3, scale = [1.0]*3, offset = [0.0]*3,
                 description = "\x00"*32):
        self.fmt = util.Format("extra_bytes_struct")
        self.packer = struct.Struct(self.fmt.pt_fmt_long)
        self.writeable = True
        self.vlr_parent = False
        self.names = [x.name for x in self.fmt.specs]

        self.data = "\x00"*192 
        self.set_property("data_type" , data_type)
        self.set_property("options" , options)
        self.set_property("name" , name + "\x00"*(32-len(description)))
        self.set_property("unused" , unused )
        self.set_property("no_data" , no_data)
        self.set_property("min" , min)
        self.set_property("max" , max)
        self.set_property("scale" , scale )
        self.set_property("offset" , offset)
        self.set_property("description" , description + "\x00"*(32-len(description)))

    def build_from_vlr(self, vlr_parent, body_offset):
        self.writeable = False
        self.data = vlr_parent.VLR_body[192*body_offset:192*(body_offset + 1)]
        self.vlr_parent = vlr_parent
        self.body_offset = body_offset
    
    def assertWriteable(self):
        if self.writeable or self.vlr_parent.reader == False:
            return
        raise util.LaspyException("""To modify VLRs and EVLRs, you must create new
                            variable length records, and then replace them via 
                            file.header.vlrs or file.header.evlrs. To do otherwise 
                            would cause data concurrency issues.""")

    def get_property_idx(self, name):
        idx = 0
        for i in self.names:
            if name == i:
                return(idx)
            idx += 1
        raise util.LaspyException("Property: " + str(name) + " not found. ")

    def get_property(self, name):
        fmt = self.fmt.specs[self.get_property_idx(name)]
        unpacked = struct.unpack(fmt.full_fmt, 
                   self.data[fmt.offs:(fmt.offs + fmt.length*fmt.num)])
        if len(unpacked) == 1:
            return(unpacked[0])
        return(unpacked)
    
    def to_byte_string(self):
        '''Return the struct as a string of raw bytes. This is useful for providing
        the struct to a VLR instance via VLR_body.'''
        return(self.data)

    def set_property(self, name, value):
        self.assertWriteable()
        fmt = self.fmt.specs[self.get_property_idx(name)]
        if isinstance(value, int) or isinstance(value, str):
            packed = struct.pack(fmt.full_fmt, value)
            self.data = self.data[0:fmt.offs] + packed + self.data[fmt.offs + len(packed):len(self.data)]  
        else: 
            packed = struct.pack(fmt.full_fmt, *value)
            self.data = self.data[0:fmt.offs] + packed + self.data[fmt.offs + len(packed):len(self.data)]  

        if self.vlr_parent != False:
            idx_start = 192*self.body_offset
            idx_stop = 192*(self.body_offset + 1) 
            d1 = self.vlr_parent.VLR_body[0:idx_start]
            d2 = self.vlr_parent.VLR_body[idx_stop:len(self.vlr_parent.VLR_body)]
            self.vlr_parent.VLR_body = (d1 + self.data + d2)
        return

    def get_reserved(self):
        return(self.get_property("reserved"))
    def set_reserved(self, value):
        self.set_property("reserved", value)
    reserved = property(get_reserved, set_reserved, None, None)

    def get_data_type(self):
        return(self.get_property("data_type"))
    def set_data_type(self, value):
        self.set_property("data_type", value)
    data_type = property(get_data_type, set_data_type, None, None)

    def get_options(self):
        return(self.get_property("options"))
    def set_options(self, value):
        self.set_property("options", value)
    options = property(get_options, set_options, None, None)

    def get_name(self):
        return(self.get_property("name"))
    def set_name(self, value):
        self.set_property("name", value)
    name = property(get_name, set_name, None, None)

    def get_no_data(self):
        return(self.get_property("no_data"))
    def set_no_data(self, value):
        self.set_property("no_data", value)
    no_data = property(get_no_data, set_no_data, None, None)

    def get_min(self):
        return(self.get_property("min"))
    def set_min(self, value):
        self.set_property("min", value)
    min = property(get_min, set_min, None, None)

    def get_max(self):
        return(self.get_property("max"))
    def set_max(self, value):
        self.set_property("max", value)
    max = property(get_max, set_max, None, None)

    def get_scale(self): 
        return(self.get_property("scale"))
    def set_scale(self, value):
        self.set_property("scale", value)
    scale = property(get_scale, set_scale, None, None)

    def get_offset(self):
        return(self.get_property("offset"))
    def set_offset(self, value):
        self.set_property("offset", value)
    offset = property(get_offset, set_offset, None, None)

    def get_description(self):
        return(self.get_property("description"))
    def set_description(self):
        self.set_property(self, "description")
    description = property(get_description, set_description, None, None)

        
class EVLR(ParseableVLR):
    ''' An extended VLR as defined in LAS specification 1.4'''
    def __init__(self, user_id, record_id, VLR_body, **kwargs):
        '''Build the EVLR using the required arguments user_id, record_id, and
        VLR_body. The user can also specify the reserved and description fields if desired.'''
        self.user_id = str(user_id) + "\x00"*(16-len(str(user_id)))
        self.record_id = record_id
        self.VLR_body = VLR_body
        self.body_fmt = None

        try: 
            self.rec_len_after_header = len(self.VLR_body) 
        except(TypeError):
            self.rec_len_after_header = 0
        if "description" in kwargs:
            self.description = str(kwargs["description"]) + "\x00"*(32-len(kwargs["description"]))
        else:
            self.description = "\x00"*32
        if "reserved" in kwargs:
            self.reserved = kwargs["reserved"]
        else:
            self.reserved = 0 
        self.fmt = util.Format("EVLR")
        self.isEVLR = True
        self.type = 0
        if self.user_id == "LASF_Spec" and self.record_id == 4:
            self.setup_extra_bytes_spec(self.VLR_body)
        try:
            self.parse_data()
        except Exception, err:
            print("Error Parsing EVLR Body Data:")
            print(err)

    def setup_extra_bytes_spec(self, VLR_body):
        self.type = 1
        self.extra_dimensions = []
        if self.rec_len_after_header % 192 != 0:
            raise util.LaspyException("""Invalid record length for extra bytes
                                     specification, must be multiple of 192.""")
        else:
            recs = self.rec_len_after_header / 192
            for i in xrange(recs):
                new_rec = ExtraBytesStruct()
                new_rec.build_from_vlr(self, i)
            self.add_extra_dim(new_rec)


    def build_from_reader(self, reader):
        '''Build an evlr from a reader capable of reading in the data.'''
        self.reserved = reader.read_words("reserved", "evlr")
        self.user_id = "".join(reader.read_words("user_id", "evlr"))
        self.record_id = reader.read_words("record_id", "evlr")
        self.rec_len_after_header = reader.read_words("rec_len_after_header", "evlr")
        self.description = "".join(reader.read_words("description", "evlr"))
        self.VLR_body = reader.read(self.rec_len_after_header)
        if self.user_id == "LASF_Spec" and self.record_id == 4:
            self.setup_extra_bytes_spec(self.VLR_body)

        ### LOGICAL CONTENT ###
        self.isEVLR = True
        self.fmt = reader.evlr_formats
        try:
            self.parse_data()
        except Exception, err:
            print("Error Parsing EVLR Body Data:")
            print(err)



    def __len__(self):
        '''Return the size of the evlr object in bytes'''
        return self.rec_len_after_header + 60

    def pack(self, name, val): 
        '''Pack an EVLR field into bytes.'''
        spec = self.fmt.lookup[name]
        if spec.num == 1:
            return(struct.pack(spec.full_fmt, val))
        return(struct.pack(spec.fmt[0]+spec.fmt[1]*len(val), *val))
    
    def to_byte_string(self):
        '''Pack the entire EVLR into a byte string.'''
        if type(self.parsed_body) != type(None):
            self.pack_data()
        out = (self.pack("reserved", self.reserved) + 
               self.pack("user_id", self.user_id) + 
               self.pack("record_id", self.record_id) + 
               self.pack("rec_len_after_header", self.rec_len_after_header) + 
               self.pack("description", self.description) +
               self.VLR_body)
        diff = (self.rec_len_after_header - len(self.VLR_body))
        if diff > 0:
            out += "\x00"*diff
        elif diff < 0:
            raise util.LaspyException("Invalid Data in EVLR: too long for specified rec_len." + 
                                " rec_len_after_header = " + str(self.rec_len_after_header) + 
                                " actual length = " + str(len(self.VLR_body)))
        return(out)


class VLR(ParseableVLR):
    '''An object to create/read/store data from LAS Variable Length Records.
    Requires three arguments: (user_id, string[16]), (record_id, int2), (VLR_body, any data with len < ~65k)'''
    def __init__(self, user_id, record_id, VLR_body, **kwargs):
        '''Build the VLR using the required arguments user_id, record_id, and VLR_body
        the user can also specify the reserved and description fields here if desired.'''
        self.user_id = str(user_id) + "\x00"*(16-len(str(user_id)))
        self.record_id = record_id
        self.VLR_body = VLR_body
        self.type = 0
        self.reader = False
        self.body_fmt = None
        try:
            self.rec_len_after_header = len(self.VLR_body)
        except(TypeError):
            self.rec_len_after_header = 0
        if "description" in kwargs:
            self.description = str(kwargs["description"]) + "\x00"*(32-len(kwargs["description"]))
        else:
            self.description = "\x00"*32
        if "reserved" in kwargs:
            self.reserved = kwargs["reserved"]
        else:
            self.reserved = 0 
        self.reserved = 0
        self.isVLR = True
        self.fmt = util.Format("VLR")
        if self.user_id == "LASF_Spec" and self.record_id == 4:
            self.setup_extra_bytes_spec(self.VLR_body)
        try:
            self.parse_data()
        except Exception, err:
            print("Error Parsing VLR Body Data:")
            print(err)



    def build_from_reader(self, reader):
        '''Build a vlr from a reader capable of reading in the data.'''
        self.reader = reader
        self.reserved = reader.read_words("reserved")
        self.user_id = "".join(reader.read_words("user_id"))
        self.record_id = reader.read_words("record_id")
        self.rec_len_after_header = reader.read_words("rec_len_after_header")
        self.description = "".join(reader.read_words("description"))
        self.VLR_body = reader.read(self.rec_len_after_header)
        if "LASF_Spec" in self.user_id and self.record_id == 4:
            self.setup_extra_bytes_spec(self.VLR_body)
        ### LOGICAL CONTENT ###
        self.isVLR = True
        self.fmt = reader.vlr_formats
        try:
            self.parse_data()
        except Exception, err:
            print("Error Parsing EVLR Body Data:")
            print(err)




    def setup_extra_bytes_spec(self, VLR_body):
        self.type = 1
        self.extra_dimensions = []
        if self.rec_len_after_header % 192 != 0:
            raise util.LaspyException("""Invalid record length for extra bytes
                                     specification, must be multiple of 192.""")
        else:
            recs = self.rec_len_after_header / 192
            for i in xrange(recs):
                new_rec = ExtraBytesStruct()
                new_rec.build_from_vlr(self, i) 
                self.add_extra_dim(new_rec)
        
    def add_extra_dim(self, new_rec):
        new_name = new_rec.name.replace("\x00", "").replace(" ", "_").lower()
        self.__dict__[new_name] = new_rec
        self.extra_dimensions.append(new_rec)


    def __len__(self):
        '''Return the size of the vlr object in bytes'''
        return self.rec_len_after_header + 54

    def pack(self, name, val): 
        '''Pack a VLR field into bytes.'''
        spec = self.fmt.lookup[name]
        if spec.num == 1:
            return(struct.pack(spec.fmt, val))
        return(struct.pack(spec.fmt[0]+spec.fmt[1]*len(val), *val))
    
    def to_byte_string(self):
        '''Pack the entire VLR into a byte string.'''
        if type(self.parsed_body) != type(None):
            self.pack_data()
        out = (self.pack("reserved", self.reserved) + 
               self.pack("user_id", self.user_id) + 
               self.pack("record_id", self.record_id) + 
               self.pack("rec_len_after_header", self.rec_len_after_header) + 
               self.pack("description", self.description) +
               self.VLR_body)
        diff = (self.rec_len_after_header - len(self.VLR_body))
        if diff > 0:
            out += "\x00"*diff
        elif diff < 0:
            raise util.LaspyException("Invalid Data in VLR: too long for specified rec_len." + 
                                " rec_len_after_header = " + str(self.rec_len_after_header) + 
                                " actual length = " + str(len(self.VLR_body)))
        return(out)

class Header(object):
    '''The low level header class. Header is built from a laspy.util.Format 
    instance, or assumes a default file format of 1.2. Header is usually interacted with via
    the HeaderManager class, an instance of which readers, writers, and file 
    objects retain a reference of.'''
    def __init__(self, file_version = 1.2, point_format = 0, **kwargs):
        # At least generate a default las format
        fmt = util.Format("h" + str(file_version))
        kwargs["version_major"] = str(file_version)[0]
        kwargs["version_minor"] = str(file_version)[2]
        self._format = fmt
        for dim in self._format.specs:
            if dim.name in kwargs.keys():
                self.__dict__[dim.name] = kwargs[dim.name]
            else:
                self.__dict__[dim.name] = dim.default
        self.file_sig = "LASF"

    def reformat(self, file_version):
        if file_version == self._format.fmt[1:4]:
            return
        new_format = util.Format("h" + str(file_version))
        self.version_major = str(file_version)[0]
        self.version_minor = str(file_version)[2]
        # Set defaults for newly available fields.
        for item in new_format.specs:
            if not item.name in self.__dict__.keys():
                self.__dict__[item.name] = item.default

        # Clear no longer available fields. 
        for item in self._format.specs:
            if not item.name in new_format.lookup.keys(): 
                self.__dict__[item.name] = None
        if str(file_version) == "1.4":
            self.point_return_count.extend([0]*10)
        self._format = new_format

    def get_format(self):
        return self._format

    doc = '''The laspy.util.Format instance of the header, builds and stores
    specifications for the data fields belonging to the header. Assigning to format
    will re-format the header.'''
    format = property(get_format, reformat, None, doc)



class HeaderManager(object):
    '''HeaderManager provides the public API for interacting with header objects. 
    It requires a Header instance and a reader/writer instance. 
    HeaderManager instances are referred to in reader/writer/file object code as header.'''
    def __init__(self, header, reader):
        '''Build the header manager object'''
        self.reader = reader
        self.writer = reader
        self._header = header 
        self.file_mode = reader.mode
        if self.file_mode == "w":
            self.allow_all_overwritables()

    def copy(self):
        return(self.__copy__())

    def __copy__(self):
        '''Populate and return a Header instance with data matching the file to which 
        the HeaderManager belongs. This is useful for creating new files with modified
        formats.'''
        self.pull()
        return copy.copy(self._header)

    def flush(self):
        '''Push all data in the header.Header instance to the file.'''
        for dim in self._header.format.specs:
            self.reader.set_header_property(dim.name, self._header.__dict__[dim.name])

    def pull(self):
        '''Load all header data from file into the header.Header instance.'''
        for dim in self._header.format.specs:
            self._header.__dict__[dim.name] = self.reader.get_header_property(dim.name)

    def allow_all_overwritables(self):
        '''Allow all specs belonging to header instance to be overwritable.'''
        for spec in self._header.format.specs:
            spec.overwritable = True

    def assertWriteMode(self):
        '''Assert that header has permission to write data to file.'''
        if self.file_mode == "r":
            raise LaspyHeaderException("Header instance is not in write mode.")

    def read_words(self, offs, fmt,num, length, pack):
        '''Read binary data'''
        self.reader.seek(offs,rel=False)
        out = self.reader._read_words(fmt, num, length)
        if pack:
            return("".join(out))
        return(out)
        
    def get_filesignature(self):
        '''Returns the file signature for the file. It should always be
        LASF'''
        return self.reader.get_header_property("file_sig")

    doc = '''The file signature for the file. Should always be LASF'''
    file_signature = property(get_filesignature, None, None, doc)

    def get_filesourceid(self):
        '''Get the file source id for the file.'''
        return self.reader.get_header_property("file_source_id")

    def set_filesourceid(self, value):
        '''Set the file source id'''
        self.assertWriteMode()
        self.writer.set_header_property("file_source_id", value)
    doc = '''The file source ID for the file.'''
    filesource_id = property(get_filesourceid, set_filesourceid, None, doc)
    file_source_id = filesource_id

    def get_global_encoding(self):
        '''Get the global encoding'''
        return(self.reader.get_header_property("global_encoding"))

    def set_global_encoding(self, value):
        self.assertWriteMode()
        self.writer.set_header_property("global_encoding", value)
        return
    doc = '''Global encoding for the file.

    From the specification:

        This is a bit field used to indicate certain global properties about
        the file. In LAS 1.2 (the version in which this field was introduced),
        only the low bit is defined (this is the bit, that if set, would have
    '''

    global_encoding = property(get_global_encoding,
                               set_global_encoding,
                               None,
                               doc)
    encoding = global_encoding


    doc = '''Indicates the meaning of GPS Time in the point records. 
             If gps_time_type is zero, then GPS Time is GPS Week Time. Otherwise
             it refers to sattelite GPS time.'''
    def get_gps_time_type(self):
        raw_encoding = self.get_global_encoding()
        return(self.reader.binary_str(raw_encoding, 16)[0])
    def set_gps_time_type(self, value):
        self.assertWriteMode()
        raw_encoding = self.reader.binary_str(self.get_global_encoding(),16)       
        self.set_global_encoding(self.reader.packed_str(str(value) 
                                + raw_encoding[1:]))
        return

    gps_time_type = property(get_gps_time_type, set_gps_time_type, None, doc)

    def get_waveform_data_packets_internal(self):
        raw_encoding = self.get_global_encoding()
        return(self.reader.binary_str(raw_encoding, 16)[1])

    def set_waveform_data_packets_internal(self, value):
        self.assertWriteMode()
        raw_encoding = self.reader.binary_str(self.get_global_encoding(), 16)
        self.set_global_encoding(self.reader.packed_str(raw_encoding[0] + str(value) + raw_encoding[2:]))
        return

    waveform_data_packets_internal = property(get_waveform_data_packets_internal, 
                                              set_waveform_data_packets_internal,
                                              None, None)

    def get_waveform_data_packets_external(self):
        raw_encoding = self.get_global_encoding()
        return(self.reader.binary_str(raw_encoding, 16)[2])

    def set_waveform_data_packets_external(self, value):
        self.assertWriteMode()
        raw_encoding = self.reader.binary_str(self.get_global_encoding(), 16)
        self.set_global_encoding(self.reader.packed_str(raw_encoding[0:2] + str(value) + raw_encoding[3:]))
        return

    waveform_data_packets_external = property(get_waveform_data_packets_external,
                                              set_waveform_data_packets_external, 
                                              None, None)
    def get_synthetic_return_num(self):
        raw_encoding = self.get_global_encoding()
        return(self.reader.binary_str(raw_encoding, 16)[3])

    def set_synthetic_return_num(self, value):
        self.assertWriteMode()
        raw_encoding = self.reader.binary_str(self.get_global_encoding(), 16)
        self.set_global_encoding(self.reader.packed_str(raw_encoding[0:3] + str(value) + raw_encoding[4:]))
        return

    synthetic_return_num = property(get_synthetic_return_num, set_synthetic_return_num, 
                                    None, None)

    def get_wkt(self):
        if self.data_format_id > 5:
            raw_encoding = self.get_global_encoding()
            return(self.reader.binary_str(raw_encoding, 16)[4])
        else:
            raise util.LaspyException("WKT not present in data_format_id " + str(self.data_format_id))

    def set_wkt(self, value):
        self.assertWriteMode()
        if self.data_format_id > 5:
            raw_encoding = self.reader.binary_str(self.get_global_encoding(), 16)
            self.set_global_encoding(self.reader.packed_str(raw_encoding[0:4] + str(value) + raw_encoding[5:]))
        else:
            raise util.LaspyException("WKT not present in data_format_id " + str(self.data_format_id))

    wkt = property(get_wkt, set_wkt, None, None)

    def get_projectid(self): 
        p1 = self.reader.get_raw_header_property("proj_id_1")
        p2 = self.reader.get_raw_header_property("proj_id_2")
        p3 = self.reader.get_raw_header_property("proj_id_3")
        p4 = self.reader.get_raw_header_property("proj_id_4") 
        return(uuid.UUID(bytes =p1+p2+p3+p4))
 
    doc = '''ProjectID for the file.  \
        laspy does not currently support setting this value from Python, as
        it is the same as :obj:`laspy.header.Header.guid`. Use that to
        manipulate the ProjectID for the file.

        From the specification:
            The four fields that comprise a complete Globally Unique Identifier
            (GUID) are now reserved for use as a Project Identifier (Project
            ID). The field remains optional. The time of assignment of the
            Project ID is at the discretion of processing software. The
            Project ID should be the same for all files that are associated
            with a unique project. By assigning a Project ID and using a File
            Source ID (defined above) every file within a project and every
            point within a file can be uniquely identified, globally.

        '''
    project_id = property(get_projectid, None, None, doc)

    def get_guid(self):
        '''Returns the GUID for the file as a :obj:`uuid.UUID` object.'''
        return self.get_projectid() 

    def set_guid(self, value):
        raw_bytes = uuid.UUID.get_bytes_le(value)
        p1 = raw_bytes[0:4]
        p2 = raw_bytes[4:6]
        p3 = raw_bytes[6:8]
        p4 = raw_bytes[8:16]
        self.reader.set_raw_header_property("proj_id_1", p1)
        self.reader.set_raw_header_property("proj_id_2", p2)
        self.reader.set_raw_header_property("proj_id_3", p3)
        self.reader.set_raw_header_property("proj_id_4", p4)

        '''Sets the GUID for the file. It must be a :class:`uuid.UUID`
        instance'''
        return
    doc = '''The GUID/:obj:`laspy.header.Header.project_id` for the file. 
    Accepts a :obj:`uuid.UUID` object.'''
    guid = property(get_guid, set_guid, None, doc)

    def get_majorversion(self):
        '''Returns the major version for the file. Expect this value to always
        be 1'''
        return self.reader.get_header_property("version_major") 

    def set_majorversion(self, value):
        '''Sets the major version for the file. Only the value 1 is accepted
        at this time'''
        self.assertWriteMode()
        self.writer.set_header_property("version_major", value)
        return
    doc = '''The major version for the file, always 1'''
    major_version = property(get_majorversion, set_majorversion, None, doc)
    version_major = major_version
    major = major_version

    def get_minorversion(self):
        '''Returns the minor version of the file. Expect this value to always
        be 0, 1, or 2'''
        return self.reader.get_header_property("version_minor") 

    def set_minorversion(self, value):
        '''Sets the minor version of the file. The value should be 0 for 1.0
        LAS files, 1 for 1.1 LAS files ...'''
        self.assertWriteMode()
        self.writer.set_header_property("version_minor",value)
        return 
    doc = '''The minor version for the file.'''
    minor_version = property(get_minorversion, set_minorversion, None, doc)
    version_minor = minor_version
    minor = minor_version

    def set_version(self, value):
        major, minor = value.split('.')
        self.assertWriteMode()
        self.writer.set_header_property("version_major", int(major))
        self.writer.set_header_property("version_minor", int(minor))

    def get_version(self):
        major = self.reader.get_header_property("version_major") 
        minor = self.reader.get_header_property("version_minor") 
        return '%d.%d' % (major, minor)
    doc = '''The version as a dotted string for the file (ie, '1.0', '1.1',
    etc)'''
    version = property(get_version, set_version, None, doc)

    def get_systemid(self):
        '''Returns the system identifier specified in the file'''
        return self.reader.get_header_property("system_id")

    def set_systemid(self, value):
        '''Sets the system identifier. The value is truncated to 31
        characters'''
        self.assertWriteMode()
        self.writer.set_header_property("system_id", value)
        return
    doc = '''The system ID for the file'''
    system_id = property(get_systemid, set_systemid, None, doc)

    def get_softwareid(self):
        '''Returns the software identifier specified in the file'''
        return self.reader.get_header_property("software_id")

    def set_softwareid(self, value):
        '''Sets the software identifier.
        '''
        self.assertWriteMode()
        return(self.writer.set_header_property("software_id", value))
    doc = '''The software ID for the file''' 
    software_id = property(get_softwareid, set_softwareid, None, doc)

    def get_date(self):
        '''Return the header's date as a :obj:`datetime.datetime`. If no date is set
        in the header, None is returned.

        Note that dates in LAS headers are not transitive because the header
        only stores the year and the day number.
        '''
        day = self.reader.get_header_property("created_day") 
        year = self.reader.get_header_property("created_year")

        if year == 0 and day == 0:
            return None
        return datetime.datetime(year,1,1) + datetime.timedelta(day - 1)

    def set_date(self, value=datetime.datetime.now()):
        '''Set the header's date from a :obj:`datetime.datetime` instance.
        '''
        self.assertWriteMode()
        delta = value - datetime.datetime(value.year, 1, 1)
        self.writer.set_header_property("created_day", delta.days + 1)
        self.writer.set_header_property("created_year", value.year)
        return

    doc = '''The header's date from a :class:`datetime.datetime` instance.

        :arg value: :class:`datetime.datetime` instance or none to use the \
        current time


        >>> t = datetime.datetime(2008,3,19)
        >>> hdr.date = t
        >>> hdr.date
        datetime.datetime(2008, 3, 19, 0, 0)

        .. note::
            LAS files do not support storing full datetimes in their headers,
            only the year and the day number. The conversion is handled for
            you if you use :class:`datetime.datetime` instances, however.
        '''
    date = property(get_date, set_date, None, doc)

    def get_headersize(self):
        '''Return the size of the header block of the LAS file in bytes.
        '''
        return self.reader.get_header_property("header_size")

    def set_headersize(self, val):
        self.assertWriteMode()
        self.writer.set_header_property("header size", val)
    doc = '''The header size for the file. You probably shouldn't touch this.''' 
    header_size = property(get_headersize, set_headersize, None, doc)
    header_length = header_size

    def get_dataoffset(self):
        '''Returns the location in bytes of where the data block of the LAS
        file starts'''
        return self.reader.get_header_property("data_offset")

    def set_dataoffset(self, value):
        '''Sets the data offset

        Any space between this value and the end of the VLRs will be written
        with 0's
        '''
        self.assertWriteMode()
        ## writer.set_padding handles data offset update.
        self.writer.set_padding(value-self.writer.vlr_stop) 
        return
    doc = '''The offset to the point data in the file. This can not be smaller then the header size + VLR length. '''
    data_offset = property(get_dataoffset, set_dataoffset, None, doc)

    def get_padding(self):
        '''Returns number of bytes between the end of the VLRs and the 
           beginning of the point data.'''
        return self.reader.get_padding() 

    def set_padding(self, value):
        '''Sets the header's padding.
        '''
        self.assertWriteMode()
        self.writer.set_padding(value)
        return
    doc = '''The number of bytes between the end of the VLRs and the 
    beginning of the point data.
    '''
    padding = property(get_padding, set_padding, None, doc)

    def get_recordscount(self):
        return self.reader.get_pointrecordscount()
    doc = '''Returns the number of user-defined header records in the header. 
    '''
    records_count = property(get_recordscount, None, None, doc) 

    def get_dataformatid(self):
        '''The point format value as an integer
        '''
        return self.reader.get_header_property("data_format_id") 

    def set_dataformatid(self, value):
        '''Set the data format ID. This is only available for files in write mode which have not yet been given points.'''
        if value not in range(6):
            raise LaspyHeaderException("Format ID must be 3, 2, 1, or 0")
        if not self.file_mode in ("w", "w+"):
            raise LaspyHeaderException("Point Format ID can only be set for " + 
                                        "files in write or append mode.")
        if self.writer.get_pointrecordscount() > 0:
            raise LaspyHeaderException("Modification of the format of existing " + 
                                        "points is not currently supported. Make " + 
                                        "your modifications in numpy and create " + 
                                        "a new file.")
        self.writer.set_header_property("data_format_id", value)
        return 
    '''The data format ID for the file, determines what point fields are present.'''
    dataformat_id = property(get_dataformatid, set_dataformatid, None, doc)
    data_format_id = dataformat_id
    

    def get_datarecordlength(self):
        '''Return the size of each point record'''
        #lenDict = {0:20,1:28,2:26,3:34,4:57,5:63}
        #return lenDict[self.data_format_id] 
        return(self.reader.get_header_property("data_record_length"))

    doc = '''The length of each point record.'''
    data_record_length = property(get_datarecordlength,
                                  None,
                                  None,
                                  doc)

    def get_schema(self):
        '''Get the :obj:`laspy.base.Format` object for the header instance.'''
        return(self.reader.header_format)

    doc = '''The header format for the file. Supports .xml and .etree methods.'''
    def set_schema(self, value):
        if self.file_mode != "w": 
            raise NotImplementedError("Converseion between formats is not supported.")
        else:
            self.reader.header_format = value
    schema = property(get_schema, set_schema, None, doc) 
    header_format = schema
    def get_compressed(self):
        return(self.reader.point_format.compressed)


    def set_compressed(self, value):
        self.reader.point_format.compressed = value
        self.reader.compressed = value
        return
    doc = '''Controls compression for this file.

    If True, the file is compressed with lasZIP compression and will
    be written with lasZIP compression.  If False, the file is not
    compressed. Not implemented in laspy.
    '''

    compressed = property(get_compressed, set_compressed, None, doc)

    def get_pointrecordscount(self):
        '''Returns the expected number of point records in the file.
        .. note::
            This value can be grossly out of sync with the actual number of records
        '''
        return self.reader.get_pointrecordscount()

    def set_pointrecordscount(self, value):
        if not self.file_mode in ("w", "w+","rw"):
            raise LaspyHeaderException("File must be open in a write mode to modify point_records_count.")
        self.writer.set_header_property("point_records_count", value)
        
        '''Sets the number of point records expected in the file.

        .. note::
            Don't use this unless you have a damn good reason to. As you write
            points to a file, laspy is going to keep this up-to-date for you
            and write it back into the header of the file once the file is
            closed after writing data.
        '''
        return
    set_count = set_pointrecordscount
    get_count = get_pointrecordscount
    point_records_count = property(get_pointrecordscount,
                                   set_pointrecordscount)
    count = point_records_count 

    __len__ = get_pointrecordscount

    def get_pointrecordsbyreturncount(self):
        '''Gets the histogram of point records by return number for returns
        0...8
        '''

        return self.reader.get_header_property("point_return_count")   

    def set_pointrecordsbyreturncount(self, value):

        '''Sets the histogram of point records by return number from a list of
        returns 0..8
        Preferred method is to use header.update_histogram.
        '''
        self.assertWriteMode()
        self.writer.set_header_property("point_return_count", value)
        return  
    doc = '''The histogram of point records by return number.''' 
    point_return_count = property(get_pointrecordsbyreturncount,
                                  set_pointrecordsbyreturncount,
                                  None,
                                  doc)
    return_count = point_return_count

    def update_histogram(self):
        '''Update the histogram of returns by number'''
        rawdata = self.writer.get_return_num()
        rawdata[rawdata == 0] = 1#

        #if self.version == "1.3":
        #    histDict = {1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0}
        #elif self.version in ["1.0", "1.1", "1.2"]:
        #    histDict = {1:0, 2:0, 3:0, 4:0, 5:0}
        #else:
        #    raise LaspyException("Invalid file version: " + self.version)
        #for i in rawdata:
        #    histDict[i] += 1        
        #raw_hist = histDict.values()
        #if self.data_format_id in (range(6)):
        if self.version != "1.4":
            raw_hist = np.histogram(rawdata, bins = range(1,7))
            
        else:
            raw_hist = np.histogram(rawdata, bins = range(1,17)) 
        #print("Raw Hist: " + str(raw_hist))
        #t = raw_hist[0][4]
        #for ret in [3,2,1,0]:
        #    raw_hist[0][ret] -= t
        #    t += raw_hist[0][ret]
        try:
            self.writer.set_header_property("point_return_count", raw_hist[0])
        except(util.LaspyException):
            raise util.LaspyException("There was an error updating the num_points_by_return header field. " + 
        "This is often caused by mal-formed header information. LAS Specifications differ on the length of this field, "+ 
        "and it is therefore important to set the header version correctly. In the meantime, try File.close(ignore_header_changes = True)" 
        )
    def update_min_max(self, minmax_mode ="scaled"):
        '''Update the min and max X,Y,Z values.'''
        if minmax_mode == "scaled":
            scale=True
        elif minmax_mode != "scaled":
            scale=False
        x = self.writer.get_x(scale)
        y = self.writer.get_y(scale)
        z = self.writer.get_z(scale)
        self.writer.set_header_property("x_max", np.max(x))
        self.writer.set_header_property("x_min", np.min(x))
        self.writer.set_header_property("y_max", np.max(y))
        self.writer.set_header_property("y_min", np.min(y))
        self.writer.set_header_property("z_max", np.max(z))
        self.writer.set_header_property("z_min", np.min(z))

    def get_scale(self):
        '''Gets the scale factors in [x, y, z] for the point data.
        '''
        return([self.reader.get_header_property(x) for x in 
                ["x_scale","y_scale", "z_scale"]])

    def set_scale(self, value):
        '''Sets the scale factors in [x, y, z] for the point data.
        '''
        self.assertWriteMode()
        self.writer.set_header_property("x_scale", value[0])
        self.writer.set_header_property("y_scale", value[1])
        self.writer.set_header_property("z_scale", value[2])
        return
    doc = '''The scale factors in [x, y, z] for the point data. 
            From the specification:
            The scale factor fields contain a double floating point value that
            is used to scale the corresponding X, Y, and Z long values within
            the point records. The corresponding X, Y, and Z scale factor must
            be multiplied by the X, Y, or Z point record value to get the
            actual X, Y, or Z coordinate. For example, if the X, Y, and Z
            coordinates are intended to have two decimal point values, then
            each scale factor will contain the number 0.01

        Coordinates are calculated using the following formula(s):
            * x = (x_int * x_scale) + x_offset
            * y = (y_int * y_scale) + y_offset
            * z = (z_int * z_scale) + z_offset
    '''
    scale = property(get_scale, set_scale, None, doc)

    def get_offset(self):
        '''Gets the offset factors in [x, y, z] for the point data.
        '''
        return([self.reader.get_header_property(x) for x in 
                ["x_offset", "y_offset", "z_offset"]])

    def set_offset(self, value):
        '''Sets the offset factors in [x, y, z] for the point data.
        '''
        self.assertWriteMode()
        self.writer.set_header_property("x_offset", value[0])
        self.writer.set_header_property("y_offset", value[1])
        self.writer.set_header_property("z_offset", value[2])
        return
    doc = '''The offset factors in [x, y, z] for the point data.

        From the specification:
            The offset fields should be used to set the overall offset for the
            point records. In general these numbers will be zero, but for
            certain cases the resolution of the point data may not be large
            enough for a given projection system. However, it should always be
            assumed that these numbers are used. So to scale a given X from
            the point record, take the point record X multiplied by the X
            scale factor, and then add the X offset.

        Coordinates are calculated using the following formula(s):
            * x = (x_int * x_scale) + x_offset
            * y = (y_int * y_scale) + y_offset
            * z = (z_int * z_scale) + z_offset

        >>> hdr.offset
        [0.0, 0.0, 0.0]
        >>> hdr.offset = [32, 32, 256]
        >>> hdr.offset
        [32.0, 32.0, 256.0]

    '''
    offset = property(get_offset, set_offset, None, doc)

    def get_min(self):
        '''Gets the minimum values of [x, y, z] for the data.
            For an accuarate result, run header.update_min_max()
            prior to use. 
        '''
        return([self.reader.get_header_property(x) for x in 
                ["x_min", "y_min", "z_min"]])

    def set_min(self, value):
        '''Sets the minimum values of [x, y, z] for the data.
        Preferred method is to use header.update_min_max.
        '''
        self.assertWriteMode()
        self.writer.set_header_property("x_min", value[0])
        self.writer.set_header_property("y_min", value[1])
        self.writer.set_header_property("z_min", value[2]) 
        return

    doc = '''The minimum values of [x, y, z] for the data in the file. 

        >>> hdr.min
        [0.0, 0.0, 0.0]
        >>> hdr.min = [33452344.2333, 523442.344, -90.993]
        >>> hdr.min
        [33452344.2333, 523442.34399999998, -90.992999999999995]

    '''
    min = property(get_min, set_min, None, doc)

    def get_max(self):
        '''Get the maximum X, Y and Z values as specified in the header. This may be out of date if you have changed data without running
        update_min_max'''
        return([self.reader.get_header_property(x) for x in ["x_max", "y_max", "z_max"]])
    def set_max(self, value):
        '''Sets the maximum values of [x, y, z] for the data.
        Preferred method is header.update_min_max()
        '''
        self.assertWriteMode()
        self.writer.set_header_property("x_max", value[0])
        self.writer.set_header_property("y_max", value[1])
        self.writer.set_header_property("z_max", value[2])
        return

    doc = '''The maximum values of [x, y, z] for the data in the file.
    '''
    max = property(get_max, set_max, None, doc)
    

    def get_start_wavefm_data_record(self):
        if not self.version in ("1.3", "1.4"):
            raise util.LaspyException("Waveform data not present in version: " + self.version)
        return(self.reader.get_header_property("start_wavefm_data_rec"))

    def set_start_wavefm_data_record(self, value):
        self.assertWriteMode()
        if not self.version in ("1.3", "1.4"):
            raise util.LaspyException("Waveform data not present in version: " + self.version)
        self.reader.set_header_property("start_wavefm_data_rec", value)

    start_wavefm_data_rec = property(get_start_wavefm_data_record, set_start_wavefm_data_record, None, None)

    def get_start_first_evlr(self):
        if not self.version == "1.4":
            raise util.LaspyException("EVLRs are present explicitly only in version 1.4")
        return(self.reader.get_header_property("start_first_evlr"))

    def set_start_first_evlr(self, value):
        if not self.version == "1.4":
            raise util.LaspyException("EVLRs are present explicitly only in version 1.4")
        self.reader.set_header_property("start_first_evlr",value)
        return

    start_first_evlr = property(get_start_first_evlr, set_start_first_evlr, None, None)

    def get_num_evlrs(self):
        if not self.version == "1.4":
            raise util.LaspyException("EVLRs are present explicitly only in version 1.4")
        return(self.reader.get_header_property("num_evlrs"))

    def set_num_evlrs(self, value):
        if not self.version == "1.4":
            raise util.LaspyException("EVLRs are present explicitly only in version 1.4")
        self.assertWriteMode()
        self.reader.set_header_property("num_evlrs", value)
    # Encourage users to use len(file.header.vlrs) 
    #num_evlrs = property(get_num_evlrs, set_num_evlrs, None, None)

    def get_legacy_point_records_count(self):
        if not self.version == "1.4":
            raise util.LaspyException("Point records count is only denoted as legacy in version 1.4 files.")
        return(self.reader.get_header_property("legacy_point_records_count"))

    def set_legacy_point_records_count(self, value):
        if not self.version == "1.4":
            raise util.LaspyException("Point records count is only denoted as legacy in version 1.4 files.")
        self.reader.set_header_property("legacy_point_records_count", value)
    
    legacy_point_records_count = property(get_legacy_point_records_count, set_legacy_point_records_count, None, None)


    def get_legacy_point_return_count(self):
        if not self.version == "1.4":
            raise util.LaspyException("Point return count is only denoted as legacy in version 1.4 files.")
        return(self.reader.get_header_property("legacy_point_return_count"))

    def set_legacy_point_return_count(self, value):
        if not self.version == "1.4":
            raise util.LaspyException("Point return count is only denoted as legacy in version 1.4 files.")
        self.reader.set_header_property("legacy_point_return_count", value)

    legacy_point_return_count = property(get_legacy_point_return_count, set_legacy_point_return_count, None, None)

    def xml(self):
        '''Return an xml repreentation of header data. (not implemented)'''
        raise NotImplementedError
    
    def etree(self):
        '''Return an etree representation of header data. (not implemented)'''
        raise NotImplementedError

    def add_vlr(self, value):
        return
   
    def get_vlrs(self):
        return(self.reader.get_vlrs())

    def set_vlrs(self, value):
       self.assertWriteMode()
       self.reader.set_vlrs(value)
       return

    doc = '''Get/set the VLR`'s for the header as a list
        VLR's are completely overwritten, so to append a VLR, first retreive
        the existing list with get_vlrs and append to it.
        '''
    vlrs = property(get_vlrs, set_vlrs, None, doc)

    def save_vlrs(self):
        '''Write any changes to the VLRs to the file.'''
        self.assertWriteMode()
        self.writer.save_vlrs()

    def get_evlrs(self):
        return(self.reader.get_evlrs())
    def set_evlrs(self, value):
        self.assertWriteMode()
        self.reader.set_evlrs(value)

    evlrs = property(get_evlrs, set_evlrs, None, None)

    def get_srs(self):
        raise NotImplementedError 

    def set_srs(self, value):
        raise NotImplementedError

    srs = property(get_srs, set_srs)

