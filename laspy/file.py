import base
import util
import header
import copy
import os

class File(object):
    ''' Base file object in laspy. Provides access to most laspy functionality,
    and holds references to the HeaderManager, Reader, and potentially Writer objects. 
    '''
    def __init__(self, filename,
                       header=None,
                       vlrs=False,
                       mode='r',
                       in_srs=None,
                       out_srs=None,
                       evlrs = False):
        '''Instantiate a file object to represent an LAS file.

        :arg filename: The filename to open
        :keyword header: A header open the file with. Not required in modes "r" and "rw"
        :type header: a :obj:`laspy.header.Header` instance
        :keyword mode: "r" for read, "rw" for modify/update, "w" for write, and "w+" for append (not implemented)
        :type mode: string
        :keyword in_srs: Input SRS to override the existing file's SRS with (not implemented)
        :type in_srs: a :obj:`laspy.SRS` instance
        :keyword out_srs: Output SRS to reproject points on-the-fly to as \
        they are read/written. (not implemented)
        :type out_srs: a :obj:`laspy.SRS` instance (not implemented)

        .. note::
            To open a file in write mode, you must provide a
            laspy.header.Header instance which will be immediately written to
            the file. If you provide a header instance in read mode, the
            values of that header will be used in place of those in the actual
            file.

        .. note::
            If a file is open for write, it cannot be opened for read and vice
            versa.

        >>> import laspy 
        >>> f = laspy.file.File('file.las', mode='r')
        >>> for p in f:
        ...     print 'X,Y,Z: ', p.x, p.y, p.z

        >>> h = f.header
        >>> f2 = file.File('file2.las', mode = "w", header=h)
        >>> points = f.points
        >>> f2.points = points
        >>> f2.close()
        '''
        if filename is not None:
            self.filename = os.path.abspath(filename)
        else:
            self.filename = None
        self._header = header
        self._vlrs = vlrs
        self._evlrs = evlrs
        self._mode = mode.lower()
        self.in_srs = in_srs
        self.out_srs = out_srs
        self.open()

    def open(self):
        '''Open the file for processing, called by __init__
        '''
       
        if self._mode == 'r':
            if not os.path.exists(self.filename):
                raise OSError("No such file or directory: '%s'" % self.filename)
            ## Make sure we have a header
            if self._header is None:
                self._reader = base.Reader(self.filename, mode=self._mode)
                self._header = self._reader.get_header()
            else: 
                raise util.LaspyException("Headers must currently be stored in the file, you provided: " + str(self._header))
                self._reader = base.Reader(self.filename, mode = self._mode, header=self._header)

            if self.in_srs:
                self._reader.SetInputSRS(self.in_srs)
            if self.out_srs:
                self._reader.SetOutputSRS(self.out_srs)
            ## Wire up API for extra dimensions
            if self._reader.extra_dimensions != []:
                for dimension in self._reader.extra_dimensions:
                    dimname = dimension.name.replace("\x00", "").replace(" ", "_").lower()
                    self.addProperty(dimname)


        if self._mode == 'rw':
            if self._header is None:
                self._writer = base.Writer(self.filename,mode = self._mode)
                self._reader = self._writer
                self._header = self._reader.get_header()
                ## Wire up API for any extra Dimensions
                if self._writer.extra_dimensions != []:
                    for dimension in self._writer.extra_dimensions:
                        dimname = dimension.name.replace("\x00", "").replace(" ", "_").lower()
                        self.addProperty(dimname) 
            else:
                raise util.LaspyException("Headers must currently be stored in the file, you provided: " + str(self._header))
    
        if self._mode == 'w': 
            if self._header is None:
                raise util.LaspyException("Creation of a file in write mode requires a header object.")  
            if isinstance(self._header,  header.HeaderManager):
                vlrs = self._header.vlrs
                evlrs = self._header.evlrs
                self._header = self._header.copy() 
                if self._vlrs != False:
                    self._vlrs.extend(vlrs)
                else:
                    self._vlrs = vlrs
                if self._evlrs != False:
                    self._evlrs.extend(evlrs)
                else:
                    self._evlrs = evlrs

            self._writer = base.Writer(self.filename, mode = "w",
                                      header = self._header, 
                                      vlrs = self._vlrs, evlrs = self._evlrs)
            self._reader = self._writer
            ## Wire up API for any extra Dimensions
            if self._writer.extra_dimensions != []:
                for dimension in self._writer.extra_dimensions:
                    dimname = dimension.name.replace("\x00", "").replace(" ", "_").lower()
                    self.addProperty(dimname) 

        if self._mode == 'w+':
            raise NotImplementedError

        if self._reader.compressed and self._mode != "r":
            raise NotImplementedError("Compressed files / buffer objects can only be opened in mode 'r' for now")            
            

    def close(self, ignore_header_changes = False, minmax_mode="scaled"):
        '''Closes the LAS file
        '''
        if self._mode == "r":
            self._reader.close()
            self._reader = None
            self._header = None
        else: 
            self._writer.close(ignore_header_changes, minmax_mode)    
            self._reader = None
            self._writer = None
            self._header = None


    def visualize(self, mode = "default", dim = "intensity"):
        try:
            import glviewer
            glviewer.run_glviewer(self, mode= mode, dim = dim)
            return(0)
        except Exception, err:
            print("Something went wrong: ")
            print(err)
            return(1)

    def addProperty(self, name):
        def fget(self):
            return(self._reader.get_dimension(name))
        def fset(self, value):
            self.assertWriteMode()
            self._reader.set_dimension(name, value)
        setattr(self.__class__, name, property(fget, fset, None, None))

    def define_new_dimension(self, name, data_type, description):
        self.assertWriteMode()
        self._writer.define_new_dimension(name, data_type, description)
        self.addProperty(name)

    def assertWriteMode(self):
        if self._mode == "r":
            raise util.LaspyException("File is not opened in a write mode.")         

    # TO BE IMPLEMENTED
    def set_srs(self, value):
        if self._mode == "r":
            return
        else:
            return

    def set_output_srs(self,value):
        return(set_srs(value))


    def get_output_srs(self):
        return self.out_srs

    doc = '''The output :obj:`laspy.SRS` for the file.  Data will be
    reprojected to this SRS according to either the :obj:`input_srs` if it
    was set or default to the :obj:`laspy.header.Header.SRS` if it was
    not set.  The header's SRS must be valid and exist for reprojection
    to occur. GDAL support must also be enabled for the library for
    reprojection to happen.'''
    
    output_srs = property(get_output_srs, set_output_srs, None, doc)

    def set_input_srs(self, value):
        if self._mode == "r":
            return
        else:
            return 

    def get_input_srs(self):
        return self.in_srs
    doc = '''The input :obj:`laspy.SRS` for the file.  This overrides the
    :obj:`laspy.header.Header.SRS`.  It is useful in cases where the header's
    SRS is not valid or does not exist.'''
    input_srs = property(get_input_srs, set_input_srs, None, doc)

    def get_header(self):
        '''Returns the laspy.header.Header for the file''' 
        if self._mode == "r":
            return self._reader.get_header()
        else:
            return self._writer.get_header()
        return None

    def set_header(self, header):
        '''Sets the laspy.header.Header for the file.  If the file is in \
        append mode, the header will be overwritten in the file.'''
        # append mode
        if self._mode == "w+": 
            self._writer.set_header(header)
            return True
        raise util.LaspyException("The header can only be set "
                                "after file creation for files in append mode")
    doc = '''The file's :obj:`laspy.header.Header`

    .. note::
        The header class supports .xml and .etree methods.

    .. note::
        If the file is in append mode, the header will be overwritten in the
        file. Setting the header for the file when it is in read mode has no
        effect. If you wish to override existing header information with your
        own at read time, you must instantiate a new :obj:`laspy.file.File`
        instance.

    '''
    header = property(get_header, set_header, None, doc)


    def get_writer(self):
        return(self._writer)

    def set_writer(self, writer):
        self._writer = writer

    def get_reader(self):
        return(self._reader)

    def set_reader(self, reader):
        self._reader = reader
    doc = '''The file's :obj:`laspy.base.Reader` object.'''
    
    reader = property(get_reader, set_reader, None, doc)

    doc = '''The file's :obj:`laspy.base.Writer` object, if applicable.'''

    writer = property(get_writer,set_writer, None, doc)


    def get_points(self):
        '''Return a numpy array of all point data in the file'''
        return self._reader.get_points()

    def set_points(self, new_points):
        '''Set the points in the file from a valid numpy array, as generated from get_points, 
        or a list/array of laspy.base.Point instances.'''
        self.assertWriteMode()
        self._writer.set_points(new_points)
        return
    doc = '''The point data from the file. Get or set the points as either a valid numpy array, or 
    a list/array of laspy.base.Point instances. In write mode, the number of point records is set the 
    first time a dimension or point array is supplied to the file.'''
    points = property(get_points, set_points, None, doc)

    def read(self, index, nice = True):
        '''Reads the point at the given index'''
        if self._reader.get_pointrecordscount() >= index:
            return(self._reader.get_point(index, nice)) 
        else:
            raise util.LaspyException("Index greater than point records count")
        
    def get_x(self):
        return(self._reader.get_x())
    def set_x(self,x):
        self.assertWriteMode()
        self._writer.set_x(x)
        return
    
    def get_x_scaled(self):
        return(self._reader.get_x(scale =True))
    
    def set_x_scaled(self,x):
        self.assertWriteMode()
        self._writer.set_x(x, scale = True)
        return

   

    X = property(get_x, set_x, None, None)
    x = property(get_x_scaled, set_x_scaled, None, None)


    def get_y(self):
        return(self._reader.get_y())
    def set_y(self, y):
        self.assertWriteMode()
        self._writer.set_y(y)
        return
    
    def get_y_scaled(self):
        return(self._reader.get_y(scale = True))
    def set_y_scaled(self, y):
        self.assertWriteMode()
        self._writer.set_y(y, scale = True)
        return

    Y = property(get_y, set_y, None, None)
    y = property(get_y_scaled, set_y_scaled, None, None)


    def get_z(self):
        return(self._reader.get_z())
    def set_z(self, z):
        self.assertWriteMode()
        self._writer.set_z(z)    
        return

    def get_z_scaled(self):
        return(self._reader.get_z(scale = True))
    def set_z_scaled(self, z):
        self.assertWriteMode()
        self._writer.set_z(z, scale = True)    
        return


    Z = property(get_z, set_z, None, None)
    z = property(get_z_scaled, set_z_scaled, None, None)


    def get_intensity(self):
        return(self._reader.get_intensity())
    def set_intensity(self, intensity):
        self.assertWriteMode()
        self._writer.set_intensity(intensity)
        return

    intensity = property(get_intensity, set_intensity, None, None)
    Intensity = intensity

    def get_flag_byte(self):
        return(self._reader.get_flag_byte())
    def set_flag_byte(self, byte):
        self.assertWriteMode()
        self._writer.set_flag_byte(byte)
        return
    
    flag_byte = property(get_flag_byte, set_flag_byte, None, None)
    
    def get_return_num(self):
        return(self._reader.get_return_num())
    def set_return_num(self, num):
        self.assertWriteMode()
        self._writer.set_return_num(num)

    return_num = property(get_return_num, set_return_num, None, None)

    def get_num_returns(self):
        return(self._reader.get_num_returns())
    def set_num_returns(self, num):
        self.assertWriteMode()
        self._writer.set_num_returns(num)
        return

    num_returns = property(get_num_returns, set_num_returns, None, None)

    def get_scan_dir_flag(self):
        return(self._reader.get_scan_dir_flag())
    def set_scan_dir_flag(self,flag):
        self.assertWriteMode()
        self._writer.set_scan_dir_flag(flag)
        return

    scan_dir_flag = property(get_scan_dir_flag, set_scan_dir_flag, None, None)

    def get_edge_flight_line(self):
        return(self._reader.get_edge_flight_line())
    def set_edge_flight_line(self,line):
        self.assertWriteMode()
        self._writer.set_edge_flight_line(line)
        return

    edge_flight_line = property(get_edge_flight_line,
                                set_edge_flight_line, None, None)

    def get_raw_classification(self):
        return(self._reader.get_raw_classification())
    def set_raw_classification(self, classification):
        self.assertWriteMode()
        self._writer.set_raw_classification(classification)
        return

    raw_classification = property(get_raw_classification, 
                                  set_raw_classification, None, None)
    Raw_Classification = raw_classification

    def get_classification(self):
        return(self._reader.get_classification())
    def set_classification(self, classification):
        self.assertWriteMode()
        self._writer.set_classification(classification)
        return
    classification = property(get_classification, 
                              set_classification, None, None)
    Classification = classification

    def get_classification_flags(self):
        return(self._reader.get_classification_flags())
    def set_classification_flags(self,value):
        self.assertWriteMode()
        self._writer.set_classification_flags(value)

    classification_flags = property(get_classification_flags, set_classification_flags, None, None) 

    def get_scanner_channel(self):
        return(self._writer.get_scanner_channel())
    def set_scanner_channel(self, value):
        self.assertWriteMode()
        self._writer.set_scanner_channel(value)

    scanner_channel = property(get_scanner_channel, set_scanner_channel, None, None)

    def get_synthetic(self):
        return(self._reader.get_synthetic())
    def set_synthetic(self, synthetic):
        self.assertWriteMode()
        self._writer.set_synthetic(synthetic)
        return

    synthetic = property(get_synthetic, set_synthetic, None, None)
    Synthetic = synthetic 

    def get_key_point(self):
        return(self._reader.get_key_point())
    def set_key_point(self, pt):
        self.assertWriteMode()
        self._writer.set_key_point(pt)
        return

    key_point = property(get_key_point, set_key_point, None, None)
    Key_Point = key_point

    def get_withheld(self):
        return(self._reader.get_withheld())
    def set_withheld(self, withheld):
        self.assertWriteMode()
        self._writer.set_withheld(withheld)
        return

    withheld = property(get_withheld, set_withheld, None, None)
    Withheld = withheld

    def get_overlap(self):
        return(self._reader.get_overlap())
    def set_overlap(self, overlap):
        self.assertWriteMode()
        self._writer.set_overlap(overlap)
        return

    overlap = property(get_overlap, set_overlap, None, None)


    def get_scan_angle_rank(self):
        return(self._reader.get_scan_angle_rank())
    def set_scan_angle_rank(self, rank):
        self.assertWriteMode()
        self._writer.set_scan_angle_rank(rank)
        return

    scan_angle_rank = property(get_scan_angle_rank, set_scan_angle_rank,None,None)

    def get_user_data(self):
        return(self._reader.get_user_data())
    def set_user_data(self, data):
        self.assertWriteMode()
        self._writer.set_user_data(data)
        return

    user_data = property(get_user_data, set_user_data, None, None)

    def get_pt_src_id(self):
        return(self._reader.get_pt_src_id())
    def set_pt_src_id(self, data):
        self.assertWriteMode()
        self._writer.set_pt_src_id(data)
        return

    pt_src_id = property(get_pt_src_id, set_pt_src_id, None, None)

    def get_gps_time(self):
        return(self._reader.get_gps_time())
    def set_gps_time(self, data):
        self.assertWriteMode()
        self._writer.set_gps_time(data)
        return
    
    gps_time = property(get_gps_time, set_gps_time, None, None)

    def get_red(self):
        return(self._reader.get_red())
    def set_red(self, red):
        self.assertWriteMode()
        self._writer.set_red(red)
    red = property(get_red, set_red, None, None)
    Red = red

    def get_green(self):
        return(self._reader.get_green())
    def set_green(self, green):
        self.assertWriteMode()
        self._writer.set_green(green)
        return
    
    green = property(get_green, set_green, None, None)
    Green = green

    def get_blue(self):
        return(self._reader.get_blue())
    def set_blue(self, blue):
        self.assertWriteMode()
        self._writer.set_blue(blue)
        return

    blue = property(get_blue, set_blue)
    Blue = blue

    def get_wave_packet_desc_index(self):
        return(self._reader.get_wave_packet_desc_index())
    def set_wave_packet_desc_index(self,idx):
        self.assertWriteMode()
        self._writer.set_wave_packet_desc_index(idx)
        return
    
    def get_nir(self):
        return(self._reader.get_nir())
    def set_nir(self, value):
        self.assertWriteMode()
        self._writer.set_nir(value)

    nir = property(get_nir, set_nir, None, None)

    wave_packet_desc_index = property(get_wave_packet_desc_index,
                                      set_wave_packet_desc_index, None, None)
    
    def get_byte_offset_to_waveform_data(self):
        return(self._reader.get_byte_offset_to_waveform_data())
    def set_byte_offset_to_waveform_data(self, idx):
        self.assertWriteMode()
        self._writer.set_byte_offset_to_waveform_data(idx)
        return

    byte_offset_to_waveform_data = property(get_byte_offset_to_waveform_data,
                                            set_byte_offset_to_waveform_data,
                                            None, None)
    
    def get_waveform_packet_size(self):
        return(self._reader.get_waveform_packet_size())
    def set_waveform_packet_size(self, size):
        self.assertWriteMode()
        self._writer.set_waveform_packet_size(size)
        return

    waveform_packet_size = property(get_waveform_packet_size, 
                                    set_waveform_packet_size, 
                                    None, None)
    
    def get_return_point_waveform_loc(self):
        return(self._reader.get_return_point_waveform_loc())
    def set_return_point_waveform_loc(self, loc):
        self.assertWriteMode()
        self._writer.set_return_point_waveform_loc(loc)
        return

    return_point_waveform_loc = property(get_return_point_waveform_loc, 
                                      set_return_point_waveform_loc,
                                      None, None)
    
    def get_x_t(self):
        return(self._reader.get_x_t())
    def set_x_t(self,x):
        self.assertWriteMode()
        self._writer.set_x_t(x)
        return

    x_t = property(get_x_t, set_x_t, None, None)

    def get_y_t(self):
        return(self._reader.get_y_t())
    def set_y_t(self,y):
        self.assertWriteMode()
        self._writer.set_y_t(y)
        return

    y_t = property(get_y_t, set_y_t, None, None)

    def get_z_t(self):
        return(self._reader.get_z_t())
    def set_z_t(self, z):
        self.assertWriteMode()
        self._writer.set_z_t(z)

    z_t = property(get_z_t, set_z_t, None, None)

    def get_extra_bytes(self):
        return(self._reader.get_extra_bytes())
    def set_extra_bytes(self, new):
        self.assertWriteMode()
        self._writer.set_extra_bytes(new)

    doc = '''It is possible to specify a data_record_length longer than the default, 
            and the extra space is treated by laspy as raw bytes accessable via this extra_bytes property. 
            This dimension is only assignable for files in write mode which were instantiated with the appropriate
            data_record_length from the header.'''
    extra_bytes = property(get_extra_bytes, set_extra_bytes, None, doc)
        
    def __iter__(self):
        '''Iterator support (read mode only)

          >>> points = []
          >>> for i in f:
          ...   points.append(i)
          ...   print i # doctest: +ELLIPSIS
          <laspy.base.Point object at ...>
        '''
        if self._mode == "r":
            self.at_end = False
            p = self._reader.get_point(0)
            while p and not self.at_end:
                
                yield p
                p = self._reader.get_next_point()
                if not p:
                    self.at_end = True
            else:
                self.close()
                self.open()
        else:
            print("Iteration only supported in read mode, try using FileObject.points")
            yield(None)


    def __getitem__(self, index):
        '''Index and slicing support

          >>> out = f[0:3]
          [<laspy.base.Point object at ...>,
          <laspy.base.Point object at ...>,
          <laspy.base.Point object at ...>]
        '''
        try:
            index.stop
        except AttributeError:
            return self.read(index)

        output = []
        if index.step:
            step = index.step
        else:
            step = 1
        for i in range(index.start, index.stop, step):
            output.append(self.read(i))

        return output

    def __len__(self):
        '''Returns the number of points in the file according to the header'''
        return self.header.point_records_count

    def write(self, pt):
        '''Writes the point to the file if it is append or write mode. LAS
        files are written sequentially starting from the first point (in pure
        write mode) or from the last point that exists (in append mode).

        :param pt: The point to write.
        :type pt: :obj:`laspy.util.Point` instance to write

        .. note::
            At this time, it is not possible to duck-type point objects and
            have them be written into the LAS file (from say numpy or
            something). You have to take care of this adaptation yourself.

        '''
        if not isinstance(pt, util.Point):
            raise util.LaspyException('cannot write %s, it must '
                                    'be of type laspy.point.Point' % pt)
        if self._mode != "r":
            #core.las.LASWriter_WritePoint(self.handle, pt.handle)
            pass
    def __enter__(self):
        return(self)

    def __exit__(self,type, value, traceback):
        ## Updating header changes is slow.
        self.close(ignore_header_changes = True)

    def get_point_format(self):
        return self._reader.point_format

    doc = '''The point format of the file, stored as a laspy.util.Format instance. Supports .xml and .etree methods.'''
    point_format = property(get_point_format, None, None, doc)


    
#    def get_xmlsummary(self):
#        '''Returns an XML string summarizing all of the points in the reader
#        
#        .. note::
#            This method will reset the reader's read position to the 0th 
#            point to summarize the entire file, and it will again reset the 
#            read position to the 0th point upon completion.'''
#        if self._mode != 0:
#            raise util.LaspyException("file must be in read mode, not append or write mode to provide xml summary")
#        return
#        
#    summary = property(get_xmlsummary, None, None, None)
