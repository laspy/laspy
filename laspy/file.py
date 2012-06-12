"""
/******************************************************************************
 * $Id$
 *
 * Project:  laspy
 * Purpose:  Python LASFile implementation
 * Author:   Howard Butler, hobu.inc@gmail.com
 * Author:   Grant Brown, grant.brown73@gmail.com
 ******************************************************************************
 * Copyright (c) 2009, Howard Butler
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following
 * conditions are met:
 *
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in
 *       the documentation and/or other materials provided
 *       with the distribution.
 *     * Neither the name of the Martin Isenburg or Iowa Department
 *       of Natural Resources nor the names of its contributors may be
 *       used to endorse or promote products derived from this software
 *       without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 * FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 * COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 * BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
 * OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
 * AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 * OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
 * OF SUCH DAMAGE.
 ****************************************************************************/
 """


import base
import util
import copy
import os




class File(object):
    def __init__(self, filename,
                       header=None,
                       vlrs=False,
                       mode='r',
                       in_srs=None,
                       out_srs=None):
        """Instantiate a file object to represent an LAS file.

        :arg filename: The filename to open
        :keyword header: A header open the file with
        :type header: an :obj:`laspy.header.Header` instance
        :keyword mode: "r" for read, "rw" for modify/update, "w" for write, and "w+" for append
        :type mode: string
        :keyword in_srs: Input SRS to override the existing file's SRS with
        :type in_srs: an :obj:`laspy.SRS` instance
        :keyword out_srs: Output SRS to reproject points on-the-fly to as \
        they are read/written.
        :type out_srs: an :obj:`laspy.SRS` instance

        .. note::
            To open a file in write mode, you must provide a
            laspy.header.Header instance which will be immediately written to
            the file. If you provide a header instance in read mode, the
            values of that header will be used in place of those in the actual
            file.

        .. note::
            If a file is open for write, it cannot be opened for read and vice
            versa.

        >>> from laspy import file
        >>> f = file.File('file.las', mode='r')
        >>> for p in f:
        ...     print 'X,Y,Z: ', p.x, p.y, p.z

        >>> h = f.header
        >>> f2 = file.File('file2.las', header=h)
        >>> for p in f:
        ...     f2.write(p)
        >>> f2.close()
        """

        self.filename = os.path.abspath(filename)
        self._header = header
        self._vlrs = vlrs
        self._mode = mode.lower()
        self.in_srs = in_srs
        self.out_srs = out_srs

        self.open()

    def open(self):
        """Open the file for processing, called by __init__
        """
        
        if self._mode == 'r':
            if not os.path.exists(self.filename):
                raise OSError("No such file or directory: '%s'" % self.filename)
            self.reader = base.Reader(self.filename, self._mode)            

            if self._header == None:
                self._header = self.reader.get_header(self._mode)
            else:
                base.ReadWithHeader(self.filename, self._header)


            if self.in_srs:
                self.reader.SetInputSRS(self.in_srs)
            if self.out_srs:
                self.reader.SetOutputSRS(self.out_srs)

        if self._mode == 'rw':
            self.writer = base.Writer(self.filename, self._mode)
            self.reader = self.writer
            if self._header == None:
                self._header = self.reader.get_header(self._mode)
            else:
                base.ModifyWithHeader(self.filename, self._header)
    
        if self._mode == 'w':
            if self._header == None:
                raise util.LaspyException("Creation of a file in write mode requires a header object.")  
            if self._header.reader != False:
                # Do a shallow copy of header, so we don't screw it up for the 
                # read mode file.
                self._header = copy.copy(self._header)
                self._header.file_mode = "w"
                self._header.setup_writer_attrs()
            self.writer = base.Writer(self.filename, "w", 
                                      self._header, self._vlrs)
            self.reader = self.writer
        if self._mode == 'w+':
            self.extender = base.Extender(self.filename)
            if self._header == None:
                self._header = self.reader.get_header(self._mode)
            else:
                base.ExtendWithHeader(self.filename, self._header)

    #def __del__(self):
    #    # Allow GC to clean up?
    #    self.close()

    def close(self, ignore_header_changes = False):
        """Closes the LAS file
        """
        if self._mode == "r":
            self.reader.close()
        else:
            self.writer.close(ignore_header_changes)    
    
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

    doc = """The output :obj:`laspy.SRS` for the file.  Data will be
    reprojected to this SRS according to either the :obj:`input_srs` if it
    was set or default to the :obj:`laspy.header.Header.SRS` if it was
    not set.  The header's SRS must be valid and exist for reprojection
    to occur. GDAL support must also be enabled for the library for
    reprojection to happen."""
    
    output_srs = property(get_output_srs, set_output_srs, None, doc)

    def set_input_srs(self, value):
        if self._mode == "r":
            return
        else:
            return 

    def get_input_srs(self):
        return self.in_srs
    doc = """The input :obj:`laspy.SRS` for the file.  This overrides the
    :obj:`laspy.header.Header.SRS`.  It is useful in cases where the header's
    SRS is not valid or does not exist."""
    input_srs = property(get_input_srs, set_input_srs, None, doc)

    def get_header(self):
        """Returns the laspy.header.Header for the file""" 
        if self._mode == "r":
            return self.reader.get_header(self._mode)
        else:
            return self.writer.get_header(self._mode)
        return None

    def set_header(self, header):
        """Sets the laspy.header.Header for the file.  If the file is in \
        append mode, the header will be overwritten in the file."""
        # append mode
        if self._mode == "w+": 
            self.writer.set_header(header)
            return True
        raise util.LaspyException("The header can only be set "
                                "after file creation for files in append mode")
    doc = """The file's :obj:`laspy.header.Header`

    .. note::
        If the file is in append mode, the header will be overwritten in the
        file. Setting the header for the file when it is in read mode has no
        effect. If you wish to override existing header information with your
        own at read time, you must instantiate a new :obj:`laspy.file.File`
        instance.

    """
    header = property(get_header, set_header, None, doc)

    def read(self, index, nice = True):
        """Reads the point at the given index"""
        if self.reader.get_pointrecordscount() >= index:
            
            return(self.reader.get_point(index, nice)) 
        else:
            raise util.LaspyException("Index greater than point records count")
        
    def get_x(self, scale = False):
        return(self.reader.get_x(scale))
    def set_x(self,x, scale=False):
        self.assertWriteMode()
        self.writer.set_x(x, scale)
        return

    X = property(get_x, set_x, None, None)
    x = X

    def get_y(self, scale = False):
        return(self.reader.get_y(scale))
    def set_y(self, y, scale = False):
        self.assertWriteMode()
        self.writer.set_y(y, scale)
        return

    Y = property(get_y, set_y, None, None)
    y = Y

    def get_z(self, scale = False):
        return(self.reader.get_z(scale))
    def set_z(self, z, scale = False):
        self.assertWriteMode()
        self.writer.set_z(z, scale)    
        return
    Z = property(get_z, set_z, None, None)
    z = Z

    def get_intensity(self):
        return(self.reader.get_intensity())
    def set_intensity(self, intensity):
        self.assertWriteMode()
        self.writer.set_intensity(intensity)
        return

    intensity = property(get_intensity, set_intensity, None, None)
    Intensity = intensity

    def get_flag_byte(self):
        return(self.reader.get_flag_byte())
    def set_flag_byte(self, byte):
        self.assertWriteMode()
        self.writer.set_flag_byte(byte)
        return
    
    flag_byte = property(get_flag_byte, set_flag_byte, None, None)
    
    def get_return_num(self):
        return(self.reader.get_return_num())
    def set_return_num(self, num):
        self.assertWriteMode()
        self.writer.set_return_num(num)

    return_num = property(get_return_num, set_return_num, None, None)

    def get_num_returns(self):
        return(self.reader.get_num_returns())
    def set_num_returns(self, num):
        self.assertWriteMode()
        self.writer.set_num_returns(num)
        return

    num_returns = property(get_return_num, set_num_returns, None, None)

    def get_scan_dir_flag(self):
        return(self.reader.get_scan_dir_flag())
    def set_scan_dir_flag(self,flag):
        self.assertWriteMode()
        self.writer.set_scan_dir_flag(flag)
        return

    scan_dir_flag = property(get_scan_dir_flag, set_scan_dir_flag, None, None)

    def get_edge_flight_line(self):
        return(self.reader.get_edge_flight_line())
    def set_edge_flight_line(self,line):
        self.assertWriteMode()
        self.writer.set_edge_flight_line(line)
        return

    edge_flight_line = property(get_edge_flight_line,
                                set_edge_flight_line, None, None)

    def get_raw_classification(self):
        return(self.reader.get_raw_classification())
    def set_raw_classification(self, classification):
        self.assertWriteMode()
        self.writer.set_raw_classification(classification)
        return

    raw_classification = property(get_raw_classification, 
                                  set_raw_classification, None, None)
    Raw_Classification = raw_classification

    def get_classification(self):
        return(self.reader.get_classification())
    def set_classification(self, classification):
        self.assertWriteMode()
        self.writer.set_classification(classification)
        return
    classification = property(get_classification, 
                              set_classification, None, None)
    Classification = classification

    def get_synthetic(self):
        return(self.reader.get_synthetic())
    def set_synthetic(self, synthetic):
        self.assertWriteMode()
        self.writer.set_synthetic(synthetic)
        return

    synthetic = property(get_synthetic, set_synthetic, None, None)
    Synthetic = synthetic 

    def get_key_point(self):
        return(self.reader.get_key_point())
    def set_key_point(self, pt):
        self.assertWriteMode()
        self.writer.set_key_point(pt)
        return

    key_point = property(get_key_point, set_key_point, None, None)
    Key_Point = key_point

    def get_withheld(self):
        return(self.reader.get_withheld())
    def set_withheld(self, withheld):
        self.assertWriteMode()
        self.writer.set_withheld(withheld)
        return

    withheld = property(get_withheld, set_withheld, None, None)
    Withheld = withheld

    def get_scan_angle_rank(self):
        return(self.reader.get_scan_angle_rank())
    def set_scan_angle_rank(self, rank):
        self.assertWriteMode()
        self.writer.set_scan_angle_rank(rank)
        return

    scan_angle_rank = property(get_scan_angle_rank, set_scan_angle_rank,None,None)

    def get_user_data(self):
        return(self.reader.get_user_data())
    def set_user_data(self, data):
        self.assertWriteMode()
        self.writer.set_user_data(data)
        return

    user_data = property(get_user_data, set_user_data, None, None)

    def get_pt_src_id(self):
        return(self.reader.get_pt_src_id())
    def set_pt_src_id(self, data):
        self.assertWriteMode()
        self.writer.set_pt_src_id(data)
        return

    pt_src_id = property(get_pt_src_id, set_pt_src_id, None, None)

    def get_gps_time(self):
        return(self.reader.get_gps_time())
    def set_gps_time(self, data):
        self.assertWriteMode()
        self.writer.set_gps_time(data)
        return
    
    gps_time = property(get_gps_time, set_gps_time, None, None)

    def get_red(self):
        return(self.reader.get_red())
    def set_red(self, red):
        self.assertWriteMode()
        self.writer.set_red(red)
    red = property(get_red, set_red, None, None)
    Red = red

    def get_green(self):
        return(self.reader.get_green())
    def set_green(self, green):
        self.assertWriteMode()
        self.writer.set_green(green)
        return
    
    green = property(get_green, set_green, None, None)
    Green = green

    def get_blue(self):
        return(self.reader.get_blue())
    def set_blue(self, blue):
        self.assertWriteMode()
        self.writer.set_blue(blue)
        return

    blue = property(get_blue, set_blue)
    Blue = blue

    def get_wave_packet_desc_index(self):
        return(self.reader.get_wave_packet_descp_idx())
    def set_wave_packet_desc_index(self,idx):
        self.assertWriteMode()
        self.writer.set_wave_packet_descp_idx(idx)
        return

    wave_packet_desc_index = property(get_wave_packet_desc_index,
                                      set_wave_packet_desc_index, None, None)
    
    def get_byte_offset_to_waveform_data(self):
        return(self.reader.get_byte_offset_to_wavefm_data())
    def set_byte_offset_to_waveform_data(self, idx):
        self.assertWriteMode()
        self.writer.set_byte_offset_to_wavefm_data(idx)
        return

    byte_offset_to_waveform_data = property(get_byte_offset_to_waveform_data,
                                            set_byte_offset_to_waveform_data,
                                            None, None)
    
    def get_waveform_packet_size(self):
        return(self.reader.get_wavefm_pkt_size())
    def set_waveform_packet_size(self, size):
        self.assertWriteMode()
        self.writer.set_wavefm_pkt_size(size)
        return

    waveform_packet_size = property(get_waveform_packet_size, 
                                    set_waveform_packet_size, 
                                    None, None)
    
    def get_return_pt_waveform_loc(self):
        return(self.reader.get_return_pt_wavefm_loc())
    def set_return_pt_waveform_loc(self, loc):
        self.assertWriteMode()
        self.writer.set_return_pt_wavefm_loc(loc)
        return

    return_pt_waveform_loc = property(get_return_pt_waveform_loc, 
                                      set_return_pt_waveform_loc,
                                      None, None)
    
    def get_x_t(self):
        return(self.reader.get_x_t())
    def set_x_t(self,x):
        self.assertWriteMode()
        self.writer.set_x_t(x)
        return

    x_t = property(get_x_t, set_x_t, None, None)

    def get_y_t(self):
        return(self.reader.get_y_t())
    def set_y_t(self,y):
        self.assertWriteMode()
        self.writer.set_y_t(y)
        return

    y_t = property(get_y_t, set_y_t, None, None)

    def get_z_t(self):
        return(self.reader.get_z_t())
    def set_z_t(self, z):
        self.assertWriteMode()
        self.writer.set_z_t(z)

    z_t = property(get_z_t, set_z_t, None, None)


    def __iter__(self):
        """Iterator support (read mode only)

          >>> points = []
          >>> for i in f:
          ...   points.append(i)
          ...   print i # doctest: +ELLIPSIS
          <laspy.base.Point object at ...>
        """
        if self._mode == "r":
            self.at_end = False
            p = self.reader.get_point(0)
            while p and not self.at_end:
                
                yield p
                p = self.reader.get_next_point()
                if not p:
                    self.at_end = True
            else:
                self.close()
                self.open()


    ### END OF GB REVISIONS ###

    def __getitem__(self, index):
        """Index and slicing support

          >>> out = f[0:3]
          [<laspy.point.Point object at ...>,
          <laspy.point.Point object at ...>,
          <laspy.point.Point object at ...>]
        """
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
        """Returns the number of points in the file according to the header"""
        return self.header.point_records_count

    def write(self, pt):
        """Writes the point to the file if it is append or write mode. LAS
        files are written sequentially starting from the first point (in pure
        write mode) or from the last point that exists (in append mode).

        :param pt: The point to write.
        :type pt: :obj:`laspy.point.Point` instance to write

        .. note::
            At this time, it is not possible to duck-type point objects and
            have them be written into the LAS file (from say numpy or
            something). You have to take care of this adaptation yourself.

        """
        if not isinstance(pt, util.Point):
            raise util.LaspyException('cannot write %s, it must '
                                    'be of type laspy.point.Point' % pt)
        if self._mode != "r":
            #core.las.LASWriter_WritePoint(self.handle, pt.handle)
            pass

    def get_xmlsummary(self):
        """Returns an XML string summarizing all of the points in the reader
        
        .. note::
            This method will reset the reader's read position to the 0th 
            point to summarize the entire file, and it will again reset the 
            read position to the 0th point upon completion."""
        if self._mode != 0:
            raise util.LaspyException("file must be in read mode, not append or write mode to provide xml summary")
        return
        
    summary = property(get_xmlsummary, None, None, None)

