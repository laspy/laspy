import ctypes
import struct


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

fmtLen = {"<l":4, "<L":4, "<h":2, "<H":2, "<B":1, "<b":1,"<f":4, "<s":1, "<d":8, "<Q":8}
LEfmt = {"ctypes.c_long":"<l","ctypes.c_ulong":"<L", "ctypes.c_ushort":"<H", "ctypes.c_ubyte":"<B", 
        "ctypes.c_byte":"<b","ctypes.c_float":"<f", "ctypes.c_char":"<s", 
        "ctypes.c_double":"<d", "ctypes.c_ulonglong":"<Q","ctypes.c_short":"<h"}
npFmt = {"<l":"i4", "<L":"u4", "<h":"i2","<H":"u2", "<B":"u1", "<f":"f4", "<s":"S1", "<d":"f8", "<Q":"u8", "<b":"i1"}


defaults = {"<L":0,"<l":0, "<H":0, "<h":0, "<B": "0", "<b":"0", "<f":0.0, "<s":" ", "<d":0.0, "<Q":0}

edim_fmt_dict = {
    1:("ctypes.c_ubyte",1), 
    2:("ctypes.c_char",1), 
    3:("ctypes.c_ushort",1), 
    4:("ctypes.c_short",1),
    5:("ctypes.c_ulong",1), 
    6:("ctypes.c_long",1),
    7:("ctypes.c_ulonglong",1),
    8:("ctypes.c_longlong",1),
    9:("ctypes.c_float",1),
    10:("ctypes.c_double",1),
    11:("ctypes.c_ubyte",2),
    12:("ctypes.c_char",2),
    13:("ctypes.c_ushort",2),
    14:("ctypes.c_short",2),
    15:("ctypes.c_ulong",2),
    16:("ctypes.c_long",2),
    17:("ctypes.c_ulonglong",2),
    18:("ctypes.c_longlong",2),
    19:("ctypes.c_float",2),
    20:("ctypes.c_double",2),
    21:("ctypes.c_ubyte",3),
    22:("ctypes.c_char",3),
    23:("ctypes.c_ushort",3),
    24:("ctypes.c_short",3),
    25:("ctypes.c_ulong",3),
    26:("ctypes.c_long",3),
    27:("ctypes.c_ulonglong",3),
    28:("ctypes.c_longlong",3),
    29:("ctypes.c_float",3),
    30:("ctypes.c_double",3)
    }

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
            # Check if we need to do anything special to the numpy format
            if self.num > 1:
                if self.fmt == "<s":
                    self.np_fmt = "S"+str(self.num)
                elif self.fmt == "<B":
                    self.np_fmt = "V" + str(num)

                else:
                    ## We need a sub-array
                    self.np_fmt = str(self.num) + npFmt[self.fmt]            
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
        fmt.text = str(self.Format)
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
    def __init__(self, fmt, overwritable = False, extra_bytes = False, extradims = []):
        '''Build the :obj:`laspy.util.Format` instance. '''
        fmt = str(fmt)
        self.fmt = fmt
        self.overwritable = overwritable
        self.extradims = extradims
        try:
            self._etree = etree.Element("Format")
        except:
            print("There was an error initializing the etree instance, XML and " + 
                   " Etree methods may throw exceptions.")
            self._etree = False
        self.specs = []
        self.rec_len = 0
        self.pt_fmt_long = "<"
        
        self.compressed = False
        # Try to detect compression. The only values which get passed to 
        # this method which are coercible to integers are point formats. 
        # Try to detect point formats which are equivalent to a valid format
        # plus 128, which signifies a potential laz file. 
        try:
            fmt = int(fmt)
            compression_bit_7 = (fmt & 0x80) >> 7
            compression_bit_6 = (fmt & 0x40) >> 6
            if (not compression_bit_6 and compression_bit_7):
                self.compressed = True
                fmt &= 0x3f;
            fmt = str(fmt)
        except ValueError:
            pass
            
        if not (fmt in ("0", "1", "2", "3", "4", "5","6","7","8","9","10", "VLR", 
                        "EVLR", "h1.0", "h1.1", "h1.2", "h1.3", "h1.4", 
                        "extra_bytes_struct", "None")):
            raise LaspyException("Invalid format: " + str(fmt))
        if self.fmt == None:
            return
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
        self.add("reserved", "ctypes.c_ubyte", 2)
        self.add("data_type", "ctypes.c_ubyte", 1)
        self.add("options", "ctypes.c_ubyte", 1)
        self.add("name", "ctypes.c_char", 32)
        self.add("unused", "ctypes.c_ubyte", 4)
        # The meaning of the following fields is context dependent, but they're 
        # always in three blocks of eight bytes. Is there a better way to represent 
        # this data at this stage?
        self.add("no_data", "ctypes.c_double", 3)
        self.add("min", "ctypes.c_double", 3)
        self.add("max", "ctypes.c_double", 3)
        self.add("scale", "ctypes.c_double", 3)
        self.add("offset", "ctypes.c_double", 3)
        self.add("description", "ctypes.c_char", 32)

    def build_extra_bytes(self, extra_bytes):
        if not extra_bytes in (0, False): 
            self.add("extra_bytes", "ctypes.c_ubyte", extra_bytes) 

    def setup_lookup(self):
        self.lookup = {}
        for spec in self.specs:
            self.lookup[spec.name] = spec
        self.packer = struct.Struct(self.pt_fmt_long)

    def build_header(self, fmt):
        self.format_type = "header version = " + fmt[1:]
        self.add("file_sig","ctypes.c_char", 4, pack = True, overwritable=self.overwritable)
        self.add("file_source_id", "ctypes.c_ushort", 1)
        self.add("global_encoding","ctypes.c_ushort", 1)
        self.add("proj_id_1","ctypes.c_ulong", 1)
        self.add("proj_id_2", "ctypes.c_ushort", 1)
        self.add("proj_id_3", "ctypes.c_ushort", 1)
        self.add("proj_id_4", "ctypes.c_ubyte", 8)
        self.add("version_major", "ctypes.c_ubyte", 1, overwritable=self.overwritable)
        self.add("version_minor", "ctypes.c_ubyte", 1, overwritable=self.overwritable)
        self.add("system_id", "ctypes.c_char", 32, pack=True)
        self.add("software_id",  "ctypes.c_char", 32, pack = True)
        self.add("created_day", "ctypes.c_ushort", 1)
        self.add("created_year", "ctypes.c_ushort",1)
        self.add("header_size", "ctypes.c_ushort", 1, overwritable=self.overwritable)
        self.add("data_offset", "ctypes.c_ulong", 1)
        self.add("num_variable_len_recs",  "ctypes.c_ulong", 1)
        self.add("data_format_id",  "ctypes.c_ubyte", 1, overwritable=self.overwritable)
        self.add("data_record_length",  "ctypes.c_ushort", 1)
        if fmt != "h1.4":
            self.add("point_records_count", "ctypes.c_ulong", 1)         
        else:
            self.add("legacy_point_records_count", "ctypes.c_ulong", 1)
            self.add("legacy_point_return_count", "ctypes.c_ulong", 5) 
        if fmt in ("h1.0", "h1.1", "h1.2", "h1.3"):
            self.add("point_return_count", "ctypes.c_long", 5)

        self.add("x_scale", "ctypes.c_double", 1)
        self.add("y_scale", "ctypes.c_double", 1)
        self.add("z_scale", "ctypes.c_double", 1)
        self.add("x_offset", "ctypes.c_double", 1)
        self.add("y_offset", "ctypes.c_double", 1)
        self.add("z_offset", "ctypes.c_double", 1) 
        self.add("x_max", "ctypes.c_double", 1)
        self.add("x_min", "ctypes.c_double", 1)
        self.add("y_max","ctypes.c_double", 1)
        self.add("y_min","ctypes.c_double", 1)
        self.add("z_max", "ctypes.c_double", 1)
        self.add("z_min", "ctypes.c_double", 1)
        if fmt in ("h1.3", "h1.4"):
            self.add("start_wavefm_data_rec", "ctypes.c_ulonglong", 1)
        if fmt == "h1.4":
            self.add("start_first_evlr", "ctypes.c_ulonglong", 1)
            self.add("num_evlrs", "ctypes.c_ulong", 1)
            self.add("point_records_count", "ctypes.c_ulonglong", 1)
            self.add("point_return_count", "ctypes.c_ulonglong", 15)

    def build_evlr_format(self, fmt):
        self.add("reserved", "ctypes.c_ushort", 1)
        self.add("user_id", "ctypes.c_char", 16)
        self.add("record_id", "ctypes.c_ushort", 1)
        self.add("rec_len_after_header", "ctypes.c_ulonglong", 1)
        self.add("description", "ctypes.c_char", 32, pack = True)

    def build_vlr_format(self, fmt):
        self.add("reserved", "ctypes.c_ushort", 1)
        self.add("user_id", "ctypes.c_char", 16)
        self.add("record_id", "ctypes.c_ushort", 1)
        self.add("rec_len_after_header", "ctypes.c_ushort", 1)
        self.add("description", "ctypes.c_char", 32, pack = True)

    def build_point_format(self, fmt):
        if fmt in [str(x) for x in range(6)]:
            self.add("X", "ctypes.c_long", 1)
            self.add("Y", "ctypes.c_long", 1)
            self.add("Z", "ctypes.c_long", 1)
            self.add("intensity",  "ctypes.c_ushort", 1)
            self.add("flag_byte", "ctypes.c_ubyte", 1)
            self.add("raw_classification", "ctypes.c_ubyte", 1)
            self.add("scan_angle_rank", "ctypes.c_byte", 1)
            self.add("user_data",  "ctypes.c_ubyte", 1)
            self.add("pt_src_id",  "ctypes.c_ushort", 1)
            if fmt in ("1", "3", "4", "5"):
                self.add("gps_time", "ctypes.c_double", 1)
            if fmt in ("3", "5"):
                self.add("red", "ctypes.c_ushort", 1)
                self.add("green", "ctypes.c_ushort", 1)
                self.add("blue" , "ctypes.c_ushort",1)
            elif fmt == "2":
                self.add("red", "ctypes.c_ushort", 1)
                self.add("green", "ctypes.c_ushort", 1)
                self.add("blue" , "ctypes.c_ushort",1)
            if fmt == "4":
                self.add("wave_packet_desc_index", "ctypes.c_ubyte", 1)
                self.add("byte_offset_to_waveform_data", "ctypes.c_ulonglong",1)
                self.add("waveform_packet_size","ctypes.c_long", 1)
                self.add("return_point_waveform_loc",  "ctypes.c_float", 1)
                self.add("x_t", "ctypes.c_float", 1)
                self.add("y_t", "ctypes.c_float", 1)           
                self.add("z_t", "ctypes.c_float", 1)
            elif fmt == "5":
                self.add("wave_packet_desc_index", "ctypes.c_ubyte", 1)
                self.add("byte_offset_to_waveform_data", "ctypes.c_ulonglong",1)
                self.add("wavefm_pkt_size", "ctypes.c_ulong", 1)
                self.add("return_point_waveform_loc", "ctypes.c_float", 1)
                self.add("x_t", "ctypes.c_float", 1)
                self.add("y_t", "ctypes.c_float", 1)          
                self.add("z_t", "ctypes.c_float", 1)
        elif fmt in ("6", "7", "8", "9", "10"):
            self.add("X", "ctypes.c_long", 1)
            self.add("Y", "ctypes.c_long", 1)
            self.add("Z", "ctypes.c_long", 1)
            self.add("intensity", "ctypes.c_ushort", 1)
            self.add("flag_byte", "ctypes.c_ubyte", 1)
            self.add("classification_flags", "ctypes.c_ubyte", 1)
            self.add("classification_byte", "ctypes.c_ubyte", 1)
            self.add("user_data", "ctypes.c_ubyte", 1)
            self.add("scan_angle", "ctypes.c_short", 1)
            self.add("pt_src_id", "ctypes.c_ushort", 1)
            self.add("gps_time", "ctypes.c_double", 1)
        if fmt in ("7", "8", "10"):
            self.add("red", "ctypes.c_ushort", 1)
            self.add("blue", "ctypes.c_ushort", 1)
            self.add("green", "ctypes.c_ushort", 1)
        if fmt in ("8", "10"):
            self.add("nir", "ctypes.c_ushort", 1)
        if fmt in ("9", "10"):
            self.add("wave_packet_desc_index", "ctypes.c_ubyte", 1)
            self.add("byte_offset_to_waveform_data", "ctypes.c_ulonglong",1)
            self.add("wavefm_pkt_size", "ctypes.c_ulong", 1)
            self.add("return_point_waveform_loc", "ctypes.c_float", 1)
            self.add("x_t", "ctypes.c_float", 1)
            self.add("y_t", "ctypes.c_float", 1)          
            self.add("z_t", "ctypes.c_float", 1)
        # Add any available extra dimensions
        # Must be tuples or lists following [name, type, num]
        for item in self.extradims:
            newfmt = self.translate_extra_spec(item)
            self.add(newfmt[0], newfmt[1], newfmt[2])

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
        
    
    def translate_extra_spec(self, extra_dim):
        if extra_dim.data_type == 0:
            name = extra_dim.name.replace("\x00", "").replace(" ", "_").lower()
            fmt = "ctypes.c_ubyte"
            num = extra_dim.options
            return((name, fmt, num))
        else:
            spec = edim_fmt_dict[extra_dim.data_type]
            return(extra_dim.name.replace("\x00", "").replace(" ", "_").lower(), spec[0], spec[1])

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
        
    


