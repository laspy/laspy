import ctypes
from struct import pack, unpack, Struct

class LaspyException(Exception):
    """LaspyException: indicates a laspy related error."""
    pass

fmtLen = {"<L":4, "<H":2, "<B":1, "<f":4, "<s":1, "<d":8, "<Q":8}
LEfmt = {ctypes.c_long:"<L", ctypes.c_ushort:"<H", ctypes.c_ubyte:"<B"
        ,ctypes.c_float:"<f", "c_char":"<s", ctypes.c_double:"<d", ctypes.c_ulonglong:"<Q"}

class Spec():
    def __init__(self,name,offs, fmt, num, pack = False,ltl_endian = True, overwritable = True):
        if ltl_endian:
            self.name = name
            self.offs = offs
            self.Format = fmt
            self.fmt = LEfmt[fmt]
            self.length = fmtLen[self.fmt]
            self.num = num
            self.pack = pack
            self.overwritable = overwritable
        else:
            raise(LaspyException("Big endian files are not currently supported."))
    def __str__(self):
        return("Field Spec Attributes \n" +
        "Name: " + self.name + "\n"+
        "Format: " + str(self.Format) + "\n" +
        "Number: " + str(self.num) + "\n"+
        "Offset: " + str(self.offs) + "\n")

### Note: ctypes formats may behave differently across platforms. 
### Those specified here follow the bytesize convention given in the
### LAS specification. 
class Format():
    def __init__(self, fmt, overwritable = False):
        fmt = str(fmt)
        self.fmt = fmt
        self.specs = []
        self.rec_len = 0
        self.pt_fmt_long = "<"
        if not (fmt in ("0", "1", "2", "3", "4", "5", "VLR", "h1.0", "h1.1", "h1.2", "h1.3")):
            raise LaspyException("Invalid format: " + str(fmt))
        ## Point Fields
        if fmt in ("0", "1", "2", "3", "4", "5"):
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
            self.add("wave_packet_descp_idx", ctypes.c_ubyte, 1)
            self.add("byte_offset_to_wavefm_data", ctypes.c_ulonglong,1)
            self.add("wavefm_pkt_size",ctypes.c_long, 1)
            self.add("return_pt_wavefm_loc",  ctypes.c_float, 1)
            self.add("x_t", ctypes.c_float, 1)
            self.add("y_t", ctypes.c_float, 1)           
            self.add("z_t", ctypes.c_float, 1)
        elif fmt == "5":
            self.add("wave_packet_descp_idx", ctypes.c_ubyte, 1)
            self.add("byte_offset_to_wavefm_data", ctypes.c_ulonglong,1)
            self.add("wavefm_pkt_size", ctypes.c_long, 1)
            self.add("return_pt_wavefm_loc", ctypes.c_float, 1)
            self.add("x_t", ctypes.c_float, 1)
            self.add("y_t", ctypes.c_float, 1)          
            self.add("z_t", ctypes.c_float, 1)
        ## VLR Fields
        if fmt == "VLR":
            self.add("reserved", ctypes.c_ushort, 1)
            self.add("user_id", "c_char", 16)
            self.add("record_id", ctypes.c_ushort, 1)
            self.add("rec_len_after_header", ctypes.c_ushort, 1)
            self.add("description", "c_char", 32, pack = True)
        
        ## Header Fields
        if fmt[0] == "h": 
            self.add("file_sig","c_char", 4, pack = True, overwritable=overwritable)
            self.add("file_src", ctypes.c_ushort, 1)
            self.add("global_encoding",ctypes.c_ushort, 1)
            self.add("proj_id_1",ctypes.c_long, 1)
            self.add("proj_id_2", ctypes.c_ushort, 1)
            self.add("proj_id_3", ctypes.c_ushort, 1)
            self.add("proj_id_4", ctypes.c_ubyte, 8)
            self.add("version_major", ctypes.c_ubyte, 1, overwritable=overwritable)
            self.add("version_minor", ctypes.c_ubyte, 1, overwritable=overwritable)
            self.add("sys_id", "c_char", 32, pack=True)
            self.add("gen_soft",  "c_char", 32, pack = True)
            self.add("created_day", ctypes.c_ushort, 1)
            self.add("created_year", ctypes.c_ushort,1)
            self.add("header_size", ctypes.c_ushort, 1, overwritable=overwritable)
            self.add("offset_to_point_data", ctypes.c_long, 1)
            self.add("num_variable_len_recs",  ctypes.c_long, 1)
            self.add("pt_dat_format_id",  ctypes.c_ubyte, 1, overwritable=overwritable)
            self.add("pt_dat_rec_len",  ctypes.c_ushort, 1)
            self.add("num_pt_recs", ctypes.c_long, 1)         
            if fmt == "h1.3":
                self.add("num_pts_by_return",  ctypes.c_long, 7)
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
            elif fmt in ("h1.0", "h1.1", "h1.2"):
                self.add("num_pts_by_return", ctypes.c_long, 5)
                self.add("x_scale", ctypes.c_double, 1)
                self.add("y_scale", ctypes.c_double, 1)
                self.add("z_scale", ctypes.c_double, 1)
                self.add("x_offset", ctypes.c_double, 1)
                self.add("y_offset", ctypes.c_double, 1)
                self.add("z_offset", ctypes.c_double, 1) 
                self.add("x_max", ctypes.c_double, 1)
                self.add("x_min", ctypes.c_double, 1)
                self.add("y_max", ctypes.c_double, 1)
                self.add("y_min", ctypes.c_double, 1)
                self.add("z_max", ctypes.c_double, 1)
                self.add("z_min", ctypes.c_double, 1)

        self.lookup = {}
        for spec in self.specs:
            self.lookup[spec.name] = spec
        
    def add(self, name, fmt, num, pack = False, overwritable = True):
        if len(self.specs) == 0:
            offs = 0
        else:
            last = self.specs[-1]
            offs = last.offs + last.num*fmtLen[last.fmt]
        self.rec_len += num*fmtLen[LEfmt[fmt]]
        self.specs.append(Spec(name, offs, fmt, num, pack, overwritable =  overwritable))
        self.pt_fmt_long += LEfmt[fmt][1]
        self.packer = Struct(self.pt_fmt_long)
    def __str__(self):
        for spec in self.specs:
            spec.__str__()

class Point():
    def __init__(self, reader, bytestr = False, unpacked_list = False, nice = False):
        self.reader = reader 
        self.packer = self.reader.point_format.packer
        if bytestr != False:
            self.unpacked = self.packer.unpack(bytestr) 
        elif unpacked_list != False:
            self.unpacked = unpacked_list
        else:
            raise LaspyException("No byte string or attribute list supplied for point.")
        i = 0
        if nice:
            for dim in reader.point_format.specs: 
                self.__dict__[dim.name] = self.unpacked[i]
                i += 1

            #bstr = reader.binary_str(self.flag_byte)
            #self.return_num = reader.packed_str(bstr[0:3])
            #self.num_returns = reader.packed_str(bstr[3:6])
            #self.scan_dir_flag = reader.packed_str(bstr[6])
            #self.edge_flight_line = reader.packed_str(bstr[7])

            #bstr = reader.binary_str(self.raw_classification)
            #self.classification = reader.packed_str(bstr[0:5])
            #self.synthetic = reader.packed_str(bstr[5])
            #self.key_point = reader.packed_str(bstr[6])
            #self.withheld = reader.packed_str(bstr[7])       
    
    def pack(self):
        return(self.packer.pack(*self.unpacked))
        
class var_len_rec():
    def __init__(self, reader=False, attr_dict = False):
        ### VLR CONTENT ###
        if not attr_dict:
            self.reserved = reader.read_words("reserved")
            self.user_id = "".join(reader.read_words("user_id"))
            self.record_id = reader.read_words("record_id")
            self.rec_len_after_header = reader.read_words("rec_len_after_header")
            self.description = "".join(reader.read_words("description"))
            self.VLR_body = reader.read(self.rec_len_after_header)
            ### LOGICAL CONTENT ###
            self.isVLR = True
            self.fmt = reader.vlr_formats
        elif not reader:
            self.reserved = attr_dict["reserved"]
            self.user_id = attr_dict["user_id"]
            self.record_id = attr_dict["record_id"]
            self.rec_len_after_header = attr_dict["rec_len_after_header"]
            self.description = attr_dict["description"]
            self.VLR_body = attr_dict["VLR_body"]
            self.fmt = attr_dict["fmt"]
            self.isVLR = True
    
    def pack(self, name, val):
        spec = self.fmt.lookup[name]
        return(pack(spec.fmt, val))
    
    def to_byte_string(self):
        out = (self.pack("reserved", self.reserved) + 
               self.pack("user_id", self.user_id) + 
               self.pack("record_id", self.record_id) + 
               self.pack("rec_len_after_header", self.rec_len_after_header) + 
               self.pack("description", self.description) +
               self.VLR_body)
        return(out)


