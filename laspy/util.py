import ctypes
from struct import pack, unpack, Struct

try: import elementtree.ElementTree as etree
except ImportError:
    try: import cElementTree as etree
    except ImportError:
        try: import lxml.etree as etree
        except ImportError:
            import xml.etree.ElementTree as etree

class LaspyException(Exception):
    """LaspyException: indicates a laspy related error."""
    pass

fmtLen = {"<l":4, "<L":4, "<h":2, "<H":2, "<B":1, "<f":4, "<s":1, "<d":8, "<Q":8}
LEfmt = {ctypes.c_long:"<l",ctypes.c_ulong:"<L", ctypes.c_ushort:"<H", ctypes.c_ubyte:"<B"
        ,ctypes.c_float:"<f", ctypes.c_char:"<s", ctypes.c_double:"<d", ctypes.c_ulonglong:"<Q",
        ctypes.c_short:"<h"}
npFmt = {"<l":"i4", "<L":"u4", "<h":"i2","<H":"u2", "<B":"u1", "<f":"f4", "<s":"s1", "<d":"f8", "<Q":"u8"}


defaults = {"<L":0,"<l":0, "<H":0, "<h":0, "<B": "0", "<f":0.0, "<s":" ", "<d":0.0, "<Q":0}

class Spec():
    '''Holds information about how to read and write a particular field. 
        These are usually created by :obj:`laspy.util.Format` objects.'''
    def __init__(self,name,offs, fmt, num, pack = False,ltl_endian = True, overwritable = True, idx = False):
        '''Build the spec instance.'''
        if ltl_endian:
            self.name = name
            self.offs = offs
            self.Format = fmt
            self.num = num
            self.fmt = LEfmt[fmt]
            self.full_fmt = LEfmt[fmt][0] + str(self.num) + LEfmt[fmt][1]
            self.length = fmtLen[self.fmt]
            self.pack = pack
            self.np_fmt = npFmt[self.fmt]
            if self.fmt == "<B" and num > 1:
                self.np_fmt = "V" + str(num)
            
            if self.num == 1 or type(defaults[self.fmt])== str:
                self.default = defaults[self.fmt]*self.num
            else:
                self.default = [defaults[self.fmt]]*self.num
            self.overwritable = overwritable
            self.idx = idx
        else:
            raise(LaspyException("Big endian files are not currently supported."))
    def etree(self):
        spec = etree.Element("spec")
        name = etree.SubElement(spec, "name")
        name.text = self.name
        fmt = etree.SubElement(spec, "ctypes_format") 
        fmt.text = str(self.Format).split("'")[1] 
        num = etree.SubElement(spec, "number")
        num.text = str(self.num)
        return(spec)
    
    def xml(self):
        return(etree.tostring(self.etree()))

### Note: ctypes formats may behave differently across platforms. 
### Those specified here follow the bytesize convention given in the
### LAS specification. 
class Format():
    '''A Format instance consists of a set of 
    :obj:`laspy.util.Spec` objects, as well as some calculated attributes 
    and summary methods. For example, Format builds the *pt_fmt_long* 
    attribute, which provides a :obj:`struct` compatable format string to 
    pack and unpack an entire formatted object (:obj:`laspy.util.Point` in particular) in its entireity. Format additionally
    supports the :obj:`laspy.util.Format.xml` and :obj:`laspy.util.Format.etree`
    methods for interrogating the members of a format. This can be useful in finding out
    what dimensions are available from a given point format, among other things.''' 
    def __init__(self, fmt, overwritable = False, extra_bytes = False):
        '''Build the :obj:`laspy.util.Format` instance. '''
        fmt = str(fmt)
        self.fmt = fmt
        self.overwritable = overwritable
        try:
            self._etree = etree.Element("Format")
        except:
            print("There was an error initializing the etree instance, XML and " + 
                   " Etree methods may throw exceptions.")
            self._etree = False
        self.specs = []
        self.rec_len = 0
        self.pt_fmt_long = "<"
        if not (fmt in ("0", "1", "2", "3", "4", "5","6","7","8","9","10", "VLR", "EVLR", "h1.0", "h1.1", "h1.2", "h1.3", "h1.4", "extra_bytes_struct")):
            raise LaspyException("Invalid format: " + str(fmt))
        ## Point Fields
        if fmt in ([str(x) for x in range(11)]):
            self.format_type = "point format = " + fmt
            self.build_point_format(fmt)
        ## VLR Fields
        if fmt == "VLR":
            self.format_type = "VLR"
            self.build_vlr_format(fmt)
        if fmt == "EVLR":
            self.format_type = "EVLR"
            self.build_evlr_format(fmt)
        ## Header Fields
        if fmt[0] == "h": 
            self.build_header(fmt)
        if fmt == "extra_bytes_struct":
            self.build_extra_bytes_struct()
        ## Shared 
        self.build_extra_bytes(extra_bytes)
        self.setup_lookup()
        
    def build_extra_bytes_struct(self):
        self.add("reserved", ctypes.c_ubyte, 2)
        self.add("data_type", ctypes.c_ubyte, 1)
        self.add("options", ctypes.c_ubyte, 1)
        self.add("name", ctypes.c_char, 32)
        self.add("unused", ctypes.c_ubyte, 4)
        # The meaning of the following fields is context dependent, but they're 
        # always in three blocks of eight bytes. Is there a better way to represent 
        # this data at this stage?
        self.add("no_data", ctypes.c_double, 3)
        self.add("min", ctypes.c_double, 3)
        self.add("max", ctypes.c_double, 3)
        self.add("scale", ctypes.c_double, 3)
        self.add("offset", ctypes.c_double, 3)
        self.add("description", ctypes.c_char, 32)

    def build_extra_bytes(self, extra_bytes):
        if not extra_bytes in (0, False): 
            self.add("extra_bytes", ctypes.c_ubyte, extra_bytes) 

    def setup_lookup(self):
        self.lookup = {}
        for spec in self.specs:
            self.lookup[spec.name] = spec
        self.packer = Struct(self.pt_fmt_long)

    def build_header(self, fmt):
        self.format_type = "header version = " + fmt[1:]
        self.add("file_sig",ctypes.c_char, 4, pack = True, overwritable=self.overwritable)
        self.add("file_source_id", ctypes.c_ushort, 1)
        self.add("global_encoding",ctypes.c_ushort, 1)
        self.add("proj_id_1",ctypes.c_ulong, 1)
        self.add("proj_id_2", ctypes.c_ushort, 1)
        self.add("proj_id_3", ctypes.c_ushort, 1)
        self.add("proj_id_4", ctypes.c_ubyte, 8)
        self.add("version_major", ctypes.c_ubyte, 1, overwritable=self.overwritable)
        self.add("version_minor", ctypes.c_ubyte, 1, overwritable=self.overwritable)
        self.add("system_id", ctypes.c_char, 32, pack=True)
        self.add("software_id",  ctypes.c_char, 32, pack = True)
        self.add("created_day", ctypes.c_ushort, 1)
        self.add("created_year", ctypes.c_ushort,1)
        self.add("header_size", ctypes.c_ushort, 1, overwritable=self.overwritable)
        self.add("data_offset", ctypes.c_ulong, 1)
        self.add("num_variable_len_recs",  ctypes.c_ulong, 1)
        self.add("data_format_id",  ctypes.c_ubyte, 1, overwritable=self.overwritable)
        self.add("data_record_length",  ctypes.c_ushort, 1)
        if fmt != "h1.4":
            self.add("point_records_count", ctypes.c_ulong, 1)         
        else:
            self.add("legacy_point_records_count", ctypes.c_ulong, 1)
            self.add("legacy_point_return_count", ctypes.c_ulong, 5) 
        if fmt in ("h1.0", "h1.1", "h1.2", "h1.3"):
            self.add("point_return_count", ctypes.c_long, 5)

        self.add("x_scale", ctypes.c_double, 1)
        self.add("y_scale", ctypes.c_double, 1)
        self.add("z_scale", ctypes.c_double, 1)
        self.add("x_offset", ctypes.c_double, 1)
        self.add("y_offset", ctypes.c_double, 1)
        self.add("z_offset", ctypes.c_double, 1) 
        self.add("x_max", ctypes.c_double, 1)
        self.add("x_min", ctypes.c_double, 1)
        self.add("y_max",ctypes.c_double, 1)
        self.add("y_min",ctypes.c_double, 1)
        self.add("z_max", ctypes.c_double, 1)
        self.add("z_min", ctypes.c_double, 1)
        if fmt in ("h1.3", "h1.4"):
            self.add("start_wavefm_data_rec", ctypes.c_ulonglong, 1)
        if fmt == "h1.4":
            self.add("start_first_evlr", ctypes.c_ulonglong, 1)
            self.add("num_evlrs", ctypes.c_ulong, 1)
            self.add("point_records_count", ctypes.c_ulonglong, 1)
            self.add("point_return_count", ctypes.c_ulonglong, 15)
                

    def build_evlr_format(self, fmt):
        self.add("reserved", ctypes.c_ushort, 1)
        self.add("user_id", ctypes.c_char, 16)
        self.add("record_id", ctypes.c_ushort, 1)
        self.add("rec_len_after_header", ctypes.c_ulonglong, 1)
        self.add("description", ctypes.c_char, 32, pack = True)

    def build_vlr_format(self, fmt):
        self.add("reserved", ctypes.c_ushort, 1)
        self.add("user_id", ctypes.c_char, 16)
        self.add("record_id", ctypes.c_ushort, 1)
        self.add("rec_len_after_header", ctypes.c_ushort, 1)
        self.add("description", ctypes.c_char, 32, pack = True)

    def build_point_format(self, fmt):
        if fmt in [str(x) for x in range(6)]:
            self.add("X", ctypes.c_long, 1)
            self.add("Y", ctypes.c_long, 1)
            self.add("Z", ctypes.c_long, 1)
            self.add("intensity",  ctypes.c_ushort, 1)
            self.add("flag_byte", ctypes.c_ubyte, 1)
            self.add("raw_classification", ctypes.c_ubyte, 1)
            self.add("scan_angle_rank", ctypes.c_ubyte, 1)
            self.add("user_data",  ctypes.c_ubyte, 1)
            self.add("pt_src_id",  ctypes.c_ushort, 1)
            if fmt in ("1", "3", "4", "5"):
                self.add("gps_time", ctypes.c_double, 1)
            if fmt in ("3", "5"):
                self.add("red", ctypes.c_ushort, 1)
                self.add("green", ctypes.c_ushort, 1)
                self.add("blue" , ctypes.c_ushort,1)
            elif fmt == "2":
                self.add("red", ctypes.c_ushort, 1)
                self.add("green", ctypes.c_ushort, 1)
                self.add("blue" , ctypes.c_ushort,1)
            if fmt == "4":
                self.add("wave_packet_desc_index", ctypes.c_ubyte, 1)
                self.add("byte_offset_to_waveform_data", ctypes.c_ulonglong,1)
                self.add("waveform_packet_size",ctypes.c_long, 1)
                self.add("return_point_waveform_loc",  ctypes.c_float, 1)
                self.add("x_t", ctypes.c_float, 1)
                self.add("y_t", ctypes.c_float, 1)           
                self.add("z_t", ctypes.c_float, 1)
            elif fmt == "5":
                self.add("wave_packet_desc_index", ctypes.c_ubyte, 1)
                self.add("byte_offset_to_waveform_data", ctypes.c_ulonglong,1)
                self.add("wavefm_pkt_size", ctypes.c_ulong, 1)
                self.add("return_point_waveform_loc", ctypes.c_float, 1)
                self.add("x_t", ctypes.c_float, 1)
                self.add("y_t", ctypes.c_float, 1)          
                self.add("z_t", ctypes.c_float, 1)
        elif fmt in ("6", "7", "8", "9", "10"):
            self.add("X", ctypes.c_long, 1)
            self.add("Y", ctypes.c_long, 1)
            self.add("Z", ctypes.c_long, 1)
            self.add("intensity", ctypes.c_ushort, 1)
            self.add("flag_byte", ctypes.c_ubyte, 1)
            self.add("classification_flags", ctypes.c_ubyte, 1)
            self.add("classification_byte", ctypes.c_ubyte, 1)
            self.add("user_data", ctypes.c_ubyte, 1)
            self.add("scan_angle", ctypes.c_short, 1)
            self.add("pt_src_id", ctypes.c_ushort, 1)
            self.add("gps_time", ctypes.c_double, 1)
        if fmt in ("7", "8", "10"):
            self.add("red", ctypes.c_ushort, 1)
            self.add("blue", ctypes.c_ushort, 1)
            self.add("green", ctypes.c_ushort, 1)
        if fmt in ("8", "10"):
            self.add("nir", ctypes.c_ushort, 1)
        if fmt in ("9", "10"):
            self.add("wave_packet_desc_index", ctypes.c_ubyte, 1)
            self.add("byte_offset_to_waveform_data", ctypes.c_ulonglong,1)
            self.add("wavefm_pkt_size", ctypes.c_ulong, 1)
            self.add("return_point_waveform_loc", ctypes.c_float, 1)
            self.add("x_t", ctypes.c_float, 1)
            self.add("y_t", ctypes.c_float, 1)          
            self.add("z_t", ctypes.c_float, 1)

    def add(self, name, fmt, num, pack = False, overwritable = True):
        if len(self.specs) == 0:
            offs = 0
        else:
            last = self.specs[-1]
            offs = last.offs + last.num*fmtLen[last.fmt]
        self.rec_len += num*fmtLen[LEfmt[fmt]]
        self.specs.append(Spec(name, offs, fmt, num, pack, overwritable =  overwritable, idx = len(self.specs)))
        self.pt_fmt_long +=(str(num) +  LEfmt[fmt][1])

        if self._etree != False:
            self._etree.append(self.specs[-1].etree()) 
    def xml(self):
        '''Return an XML Formatted string, describing all of the :obj:`laspy.util.Spec` objects belonging to the Format.'''
        return(etree.tostring(self._etree)) 
    def etree(self):
        '''Return an XML etree object, describing all of the :obj:`laspy.util.Spec` objects belonging to the Format.'''
        return(self._etree)

    def __getitem__(self, index):
        '''Provide slicing functionality: return specs[index]'''
        try:
            index.stop
        except AttributeError:
            return self.specs[index]
        if index.step:
            step = index.step
        else:
            step = 1
        return(self.specs[index.start:index.stop:step])
    
    def __iter__(self):
        '''Provide iterating functionality for spec in specs'''
        for item in self.specs:
            yield item

class ExtraBytesStruct():
    def __init__(self, data_type = 0, options = 0, name = "\x00"*32, 
                 unused = [0]*4, no_data = [0.0]*3, min = [0.0]*3, 
                 max = [0.0]*3, scale = [0.0]*3, offset = [0.0]*3, 
                 description = "\x00"*32):
        self.fmt = Format("extra_bytes_struct")
        self.packer = Struct(self.fmt.pt_fmt_long)
        self.writeable = True
        self.vlr_parent = False
        self.names = [x.name for x in self.fmt.specs]

        self.data = "\x00"*192
        self.set_property("data_type" , data_type)
        self.set_property("options" , options)
        self.set_property("name" , name )
        self.set_property("unused" , unused )
        self.set_property("no_data" , no_data)
        self.set_property("min" , min)
        self.set_property("max" , max)
        self.set_property("scale" , scale )
        self.set_property("offset" , offset)
        self.set_property("description" , description)

    def build_from_vlr(self, vlr_parent, body_offset):
        self.writeable = False
        self.data = vlr_parent.VLR_body[192*body_offset:192*(body_offset + 1)]
        self.vlr_parent = vlr_parent
        self.body_offset = body_offset
        print("Built from VLR, name is: " + self.name)
    
    def assertWriteable(self):
        if self.writeable or self.vlr_parent.reader == False:
            return
        raise LaspyException("""To modify VLRs and EVLRs, you must create new
                            variable length records, and then replace them via 
                            file.header.vlrs or file.header.evlrs. To do otherwise 
                            would cause data concurrency issues.""")

    def get_property_idx(self, name):
        idx = 0
        for i in self.names:
            if name == i:
                return(idx)
            idx += 1
        raise LaspyException("Property: " + str(name) + " not found. ")

    def get_property(self, name):
        print("Getting Property")
        fmt = self.fmt.specs[self.get_property_idx(name)]
        unpacked = unpack(fmt.full_fmt, 
                   self.data[fmt.offs:(fmt.offs + fmt.length*fmt.num)])
        if len(unpacked) == 1:
            return(unpacked[0])
        return(unpacked)

    def set_property(self, name, value):
        print("Setting Property")
        self.assertWriteable()
        fmt = self.fmt.specs[self.get_property_idx(name)]
        if isinstance(value, int) or isinstance(value, str):
            self.data = self.data[0:fmt.offs] + pack(fmt.full_fmt, value) + self.data[fmt.offs:len(self.data)]  
        else:
            print(fmt.name)
            print(value)
            self.data = self.data[0:fmt.offs] + pack(fmt.full_fmt, *value) + self.data[fmt.offs:len(self.data)]  

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
        print("Getting Scale")
        return(self.get_property("scale"))
    def set_scale(self, value):
        print("Setting scale. ")
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



class Point():
    '''A data structure for reading and storing point data. The lastest version 
    of laspy's api does not use the Point class' reading capabilities, and it is important
    to note that reading and writing points does not require a list of point instances. 
    See :obj:`laspy.file.points` for more details'''
    def __init__(self, reader, bytestr = False, unpacked_list = False, nice = False):
        '''Build a point instance, either by being given a reader which can provide data or by a list of unpacked attributes.'''
        self.reader = reader 
        self.packer = self.reader.point_format.packer
        if bytestr != False:
            self.unpacked = self.packer.unpack(bytestr) 
        elif unpacked_list != False:
            self.unpacked = unpacked_list
        else:
            raise LaspyException("No byte string or attribute list supplied for point.")
        if nice:
            self.make_nice()
    def make_nice(self):
        '''Turn a point instance with the bare essentials (an unpacked list of data)
        into a fully populated point. Add all the named attributes it possesses, including binary fields.
        '''
        i = 0
        for dim in self.reader.point_format.specs: 
                self.__dict__[dim.name] = self.unpacked[i]
                i += 1

        bstr = self.reader.binary_str(self.flag_byte)
        self.return_num = self.reader.packed_str(bstr[0:3])
        self.num_returns = self.reader.packed_str(bstr[3:6])
        self.scan_dir_flag = self.reader.packed_str(bstr[6])
        self.edge_flight_line = self.reader.packed_str(bstr[7])

        bstr = self.reader.binary_str(self.raw_classification)
        self.classification = self.reader.packed_str(bstr[0:5])
        self.synthetic = self.reader.packed_str(bstr[5])
        self.key_point = self.reader.packed_str(bstr[6])
        self.withheld = self.reader.packed_str(bstr[7])       


    def pack(self):
        '''Return a binary string representing the point data. Slower than 
        :obj:`numpy.array.tostring`, which is used by :obj:`laspy.base.DataProvider`.'''
        return(self.packer.pack(*self.unpacked))
        
    


