import datetime
from uuid import UUID
import util
from struct import pack
#import numpypy
#import numpy as np
def leap_year(year):
    if (year % 400) == 0:
        return True
    elif (year % 100) == 0:
        return True
    elif (year % 4) == 0:
        return False
    return False

## NOTE: set_attr methods are currently not implemented. These methods need
## to update the file using reader/mmap. 
class LaspyHeaderException(Exception):
    pass


class VLR():
    def __init__(self, reader=False, attr_dict = False):
        '''Build a vlr from an attribute dictionary or a reader capable of reading in the data.'''
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
            self.fmt = util.Format("VLR")
            self.isVLR = True
        else:
            raise LaspyException("VLR Instances must be instantiated from a properly prepared reader (not reccommended) " +  
                    "or from a dictonary containing the necessary attributes (reccommended).")
    def __len__(self):
        '''Return the size of the vlr object in bytes'''
        return self.rec_len_after_header + 54

    def pack(self, name, val): 
        '''Pack a VLR field into bytes.'''
        spec = self.fmt.lookup[name]
        if spec.num == 1:
            return(pack(spec.fmt, val))
        return(pack(spec.fmt[0]+spec.fmt[1]*len(val), *val))
    
    def to_byte_string(self):
        '''Pack the entire VLR into a byte string.'''
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
            raise LaspyException("Invalid Data in VLR: too long for specified rec_len." + 
                                " rec_len_after_header = " + str(self.rec_len_after_header) + 
                                " actual length = " + str(len(self.VLR_body)))
        return(out)


class Header(object):
    def __init__(self,reader = False,file_mode = False, fmt = False , **kwargs):
        '''Build the header object'''
        #We have a reader object so there's data to be read. 
        if (reader != False):
            self.format = reader.header_format        
            self.reader = reader
            if file_mode != "r":
                self.writer = self.reader
            self.file_mode = file_mode 
            for dim in self.format.specs:
                #self.__dict__[dim.name] = self.read_words(dim.offs, dim.fmt,dim.num, dim.length, dim.pack)
                self.__dict__[dim.name] = reader.get_header_property(dim.name) 
            return
        
        else:
            self.reader = False
        ## Figure out our header format
        if fmt == False:
            self.format = util.Format("h1.2", overwritable=True)
        else:
            self.format = fmt
        #Make sure we keep vlrs here. 
        ## Figure out our file mode
        if file_mode == False:
            self.file_mode = "w"
        else:
            self.file_mode = file_mode
        ## Add attributes from kwargs - these need to be dumped to a data File
        ## once it's built.

        self.attribute_list = []
        for kw in kwargs.items():
            self.attribute_list.append(kw[0])
            self.__dict__[kw[0]] = kw[1] 
        try:
            self.__dict__["vlrs"]
        except:
            self.__dict__["vlrs"] = []
    # Where do the following functions live in the lifecycle of the header,
    # how are they different than the properties defined below?
    def refresh_attrs(self):
        '''Load up all the header properties into __dict__. The header.__dict__ is used
        to pass data around without firing the usual properties. This is useful for building a new
        file with an existing header.'''
        for spec in self.format.specs:
            self.__dict__[spec.name] = self.reader.get_header_property(spec.name)
    
    def setup_writer_attrs(self):
        '''Allow all fields to be overwritten, wire up writer, clear attribute_list.'''
        self.attribute_list = []
        self.writer = self.reader
        self.allow_all_overwritables()
    
    def allow_all_overwritables(self):
        '''Allow all specs belonging to header instance to be overwritable.'''
        for spec in self.format.specs:
            spec.overwritable = True

    def push_attrs(self):
        '''Push the current values of all the specs belonging to header instance to the file from __dict__.'''
        for spec in self.format.specs:
            self.reader.set_header_property(spec.name, self.__dict__[spec.name])

    def dump_data_to_file(self):  
        '''Push attributes in attribute_list to the file. This functionality should probably be combined with push_attrs.'''
        if self.reader == False or not self.file_mode in ("w", "rw", "w+"):
            raise LaspyHeaderException("Dump data requires a valid writer object.")
        for item in self.attribute_list:
            try:
                self.writer.set_header_property(item, self.__dict__[item])
            except:
                pass

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
        return self.file_sig
    doc = '''The file signature for the file. Should always be LASF'''
    file_signature = property(get_filesignature, None, None, doc)

    def get_filesourceid(self):
        '''Get the file source id for the file.'''
        return self.reader.get_header_property("file_src")

    def set_filesourceid(self, value):
        '''Set the file source id'''
        self.assertWriteMode()
        self.writer.set_header_property("file_src", value)
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
        raise NotImplementedError("LAS Version 1.3 not yet supported.")
    def set_waveform_data_packets_internal(self, value):
        raise NotImplementedError("LAS Version 1.3 not yet supported.")
    waveform_data_packets_internal = property(get_waveform_data_packets_internal, 
                                              set_waveform_data_packets_internal,
                                              None, None)

    def get_waveform_data_packets_external(self):
        raise NotImplementedError("LAS Version 1.3 not yet supported.")

    def set_waveform_data_packets_external(self, value):
        raise NotImplementedError("LAS Version 1.3 not yet supported.")

    waveform_data_packets_external = property(get_waveform_data_packets_external,
                                              set_waveform_data_packets_external, 
                                              None, None)
    def get_synthetic_return_num(self):
        raise NotImplementedError("LAS Version 1.3 not yet supported.")
    def set_synthetic_return_num(self, value):
        raise NotImplementedError("LAS Version 1.3 not yet supported.")
    synthetic_return_num = property(get_synthetic_return_num, set_synthetic_return_num, 
                                    None, None)








    def get_projectid(self):
        
        p1 = self.reader.get_raw_header_property("proj_id_1")
        p2 = self.reader.get_raw_header_property("proj_id_2")
        p3 = self.reader.get_raw_header_property("proj_id_3")
        p4 = self.reader.get_raw_header_property("proj_id_4") 
        return(UUID(bytes =p1+p2+p3+p4))
 
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
        raw_bytes = UUID.get_bytes_le(value)
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
        return self.reader.get_header_property("sys_id")

    def set_systemid(self, value):
        '''Sets the system identifier. The value is truncated to 31
        characters'''
        self.assertWriteMode()
        self.writer.set_header_property("sys_id", value)
        return
    doc = '''The system ID for the file'''
    system_id = property(get_systemid, set_systemid, None, doc)

    def get_softwareid(self):
        '''Returns the software identifier specified in the file'''
        return self.reader.get_header_property("gen_soft")

    def set_softwareid(self, value):
        '''Sets the software identifier.
        '''
        self.assertWriteMode()
        return(self.writer.set_header_property("gen_soft", value))
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
        if not leap_year(year):
            return datetime.datetime(year, 1, 1) + datetime.timedelta(day)
        else:
            return datetime.datetime(year, 1, 1) + datetime.timedelta(day - 1)

    def set_date(self, value=datetime.datetime.now()):
        '''Set the header's date from a :obj:`datetime.datetime` instance.
        '''
        self.assertWriteMode()
        delta = value - datetime.datetime(value.year, 1, 1)
        if not leap_year(value.year):
            self.writer.set_header_property("created_day", delta.days)
        else: 
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
        return self.reader.get_header_property("offset_to_point_data")

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
    num_vlrs = records_count

    def get_dataformatid(self):
        '''The point format value as an integer
        '''
        return self.reader.get_header_property("pt_dat_format_id") 

    def set_dataformatid(self, value):
        '''Set the data format ID. This is only available for files in write mode which have not yet been given points.'''
        if value not in range(6):
            raise LaspyHeaderException("Format ID must be 3, 2, 1, or 0")
        if not self.mode in ("w", "w+"):
            raise LaspyHeaderException("Point Format ID can only be set for " + 
                                        "files in write or append mode.")
        if self.writer.get_recordscount() > 0:
            raise LaspyHeaderException("Modification of the format of existing " + 
                                        "points is not currently supported. Make " + 
                                        "your modifications in numpy and create " + 
                                        "a new file.")
        self.writer.set_header_property("pt_dat_format_id", value)
        return 
    '''The data format ID for the file, determines what point fields are present.'''
    dataformat_id = property(get_dataformatid, set_dataformatid, None, doc)
    data_format_id = dataformat_id

    def get_datarecordlength(self):
        '''Return the size of each point record'''
        lenDict = {0:20,1:28,2:26,3:34,4:57,5:63}
        return lenDict[self.pt_dat_format_id] 
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
        raise NotImplementedError("Converseion between formats is not supported.")
    
    schema = property(get_schema, set_schema, None, doc) 
    header_format = schema
    def get_compressed(self):
        raise NotImplementedError
        #return bool(core.las.LASHeader_Compressed(self.handle)) 

    def set_compressed(self, value):
        raise NotImplementedError
        #return core.las.LASHeader_SetCompressed(self.handle, value)
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
        if not self.mode in ("w", "w+"):
            raise LaspyHeaderException("File must be open in write or append mode " + 
                                        "to change the number of point records.")
        self.writer.set_header_property("num_pt_recs", value)
        
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
        return self.reader.get_header_property("num_pts_by_return")   

    def set_pointrecordsbyreturncount(self, value):

        '''Sets the histogram of point records by return number from a list of
        returns 0..8
        Preferred method is to use header.update_histogram.
        '''
        self.assertWriteMode()
        self.writer.set_header_property("num_pts_by_return", value)
        return  
    doc = '''The histogram of point records by return number.''' 
    point_return_count = property(get_pointrecordsbyreturncount,
                                  set_pointrecordsbyreturncount,
                                  None,
                                  doc)
    return_count = point_return_count

    def update_histogram(self):
        '''Update the histogram of returns by number'''
        rawdata = map(lambda x: (x==0)*1 + (x!=0)*x, 
                     self.writer.get_return_num())
        if self.version == "1.3":
            histDict = {1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0}
        elif self.version in ["1.0", "1.1", "1.2"]:
            histDict = {1:0, 2:0, 3:0, 4:0, 5:0}
        else:
            raise LaspyException("Invalid file version: " + self.version)
        for i in rawdata:
            histDict[i] += 1        
        raw_hist = histDict.values()
        # raw_hist = np.histogram(rawdata, bins = [1,2,3,4,5,6])
        # Does the user count [1,2,3,4,5] as one point return of lenght 5, or as 5 from 1 to 5?
        #print("Raw Hist: " + str(raw_hist))
        #t = raw_hist[0][4]
        #for ret in [3,2,1,0]:
        #    raw_hist[0][ret] -= t
        #    t += raw_hist[0][ret]
        try:
            self.writer.set_header_property("num_pts_by_return", raw_hist)
        except(LaspyException):
            raise LaspyException("There was an error updating the num_points_by_return header field. " + 
        "This is often caused by mal-formed header information. LAS Specifications differ on the length of this field, "+ 
        "and it is therefore important to set the header version correctly. In the meantime, try File.close(ignore_header_changes = True)" 
        )
    def update_min_max(self):
        '''Update the min and max X,Y,Z values.'''
        x = list(self.writer.get_x())
        y = list(self.writer.get_y())
        z = list(self.writer.get_z()) 
        self.writer.set_header_property("x_max", max(x))
        self.writer.set_header_property("x_min", min(x))
        self.writer.set_header_property("y_max", max(y))
        self.writer.set_header_property("y_min", min(y))
        self.writer.set_header_property("z_max", max(z))
        self.writer.set_header_property("z_min", min(z))

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
    
    def xml(self):
        '''Return an xml repreentation of header data. (not implemented)'''
        raise NotImplementedError
    
    def etree(self):
        '''Return an etree representation of header data. (not implemented)'''
        raise NotImplementedError

    ### VLR MANIPULATION NOT IMPLEMENTED
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

    def get_srs(self):
        raise NotImplementedError 

    def set_srs(self, value):
        raise NotImplementedError

    srs = property(get_srs, set_srs)

