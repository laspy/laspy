"""
/******************************************************************************
 * $Id$
 *
 * Project:  libLAS - http://liblas.org - A BSD library for LAS format data.
 * Purpose:  Python LASFile implementation
 * Author:   Howard Butler, hobu.inc@gmail.com
 *
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
import header as lasheader


import os
import types

files = {'append': [], 'write': [], 'read': {}}
import sys


class File(object):
    def __init__(self, filename,
                       header=None,
                       mode='r',
                       in_srs=None,
                       out_srs=None):
        """Instantiate a file object to represent an LAS file.

        :arg filename: The filename to open
        :keyword header: A header open the file with
        :type header: an :obj:`liblas.header.header.Header` instance
        :keyword mode: "r" for read, "w" for write, and "w+" for append
        :type mode: string
        :keyword in_srs: Input SRS to override the existing file's SRS with
        :type in_srs: an :obj:`liblas.srs.SRS` instance
        :keyword out_srs: Output SRS to reproject points on-the-fly to as \
        they are read/written.
        :type out_srs: an :obj:`liblas.srs.SRS` instance

        .. note::
            To open a file in write mode, you must provide a
            liblas.header.Header instance which will be immediately written to
            the file. If you provide a header instance in read mode, the
            values of that header will be used in place of those in the actual
            file.

        .. note::
            If a file is open for write, it cannot be opened for read and vice
            versa.

        >>> from liblas import file
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
     
        self._mode = mode.lower()
        self.in_srs = in_srs
        self.out_srs = out_srs


        #check in the registry if we already have the file open
        if mode == 'r':
            for f in files['write'] + files['append']:
                if f == self.filename:
                    raise Exception("File %s is already open for "
                                            "write.  Close the file or delete "
                                            "the reference to it" % filename)
        else:
            # we're in some kind of write mode, and if we already have the
            # file open, complain to the user.
            for f in files['read'].keys() + files['append'] + files['write']:
                if f == self.filename:
                    raise Exception("File %s is already open. "
                                            "Close the file or delete the "
                                            "reference to it" % filename)
        self.open()

    def open(self):
        """Open the file for processing, called by __init__
        """
        
        if self._mode == 'r' or self._mode == 'rb':
            
            if not os.path.exists(self.filename):
                raise OSError("No such file or directory: '%s'" % self.filename)

            self.Reader = base.Reader(self.filename)            

            if self._header == None:
                self._header = self.Reader.GetHeader()
            else:
                base.CreateWithHeader(self.filename,
                                                        self._header)
            self.mode = 0
            try:
                files['read'][self.filename] += 1
            except KeyError:
                files['read'][self.filename] = 1

            if self.in_srs:
                self.Reader.SetInputSRS(self.in_srs)
            if self.out_srs:
                self.Reader.SetOutputSRS(self.out_srs)

        if self._mode == 'w':
            pass
        if '+' in self._mode and 'r' not in self._mode:
            pass

    #def __del__(self):
    #    # Allow GC to clean up?
    #    self.close()

    def close(self):
        """Closes the LAS file
        """
        if self.mode == 0:
            try: 
                files['read'][self.filename] -= 1
                if files['read'][self.filename] == 0:
                    files['read'].pop(self.filename)
            except KeyError:
                raise Exception("File %s was not found in accounting dictionary!" % self.filename)
            self.Reader.close()           
        else:
            try:
                files['append'].remove(self.filename)
            except:
                files['write'].remove(self.filename)
            self.Writer.close()    
     

    # TO BE IMPLEMENTED
    def set_srs(self, value):
        if self.mode == 0:
            return
        else:
            return

    def set_output_srs(self,value):
        return(set_srs(value))

    def get_output_srs(self):
        return self.out_srs

    doc = """The output :obj:`liblas.srs.SRS` for the file.  Data will be
    reprojected to this SRS according to either the :obj:`input_srs` if it
    was set or default to the :obj:`liblas.header.Header.SRS` if it was
    not set.  The header's SRS must be valid and exist for reprojection
    to occur. GDAL support must also be enabled for the library for
    reprojection to happen."""
    output_srs = property(get_output_srs, set_output_srs, None, doc)

    def set_input_srs(self, value):
        if self.mode == 0:
            return
        else:
            return 

    def get_input_srs(self):
        return self.in_srs
    doc = """The input :obj:`liblas.srs.SRS` for the file.  This overrides the
    :obj:`liblas.header.Header.SRS`.  It is useful in cases where the header's
    SRS is not valid or does not exist."""
    input_srs = property(get_input_srs, set_input_srs, None, doc)

    def get_header(self):
        """Returns the liblas.header.Header for the file""" 
        if self.mode == 0:
            return self.Reader.GetHeader()
        else:
            return self.Writer.GetHeader()
        return None

    def set_header(self, header):
        """Sets the liblas.header.Header for the file.  If the file is in \
        append mode, the header will be overwritten in the file."""
        # append mode
        if mode == 2: 
            self.Writer.set_header(header)
            return True
        raise Exception("The header can only be set "
                                "after file creation for files in append mode")
    doc = """The file's :obj:`liblas.header.Header`

    .. note::
        If the file is in append mode, the header will be overwritten in the
        file. Setting the header for the file when it is in read mode has no
        effect. If you wish to override existing header information with your
        own at read time, you must instantiate a new :obj:`liblas.file.File`
        instance.

    """
    header = property(get_header, set_header, None, doc)

    def read(self, index):
        """Reads the point at the given index"""
        if self.mode == 0:
            return(self.Reader.GetPoint(index)) 

    def get_x(self, scale = False):
        return(self.Reader.GetX(scale))
    def set_x(self, scale=False):
        return
    X = property(get_x, set_x, None, None)
    x = X

    def get_y(self, scale = False):
        return(self.Reader.GetY(scale))
    def set_y(self, scale = False):
        return
    Y = property(get_y, set_y, None, None)
    y = Y

    def get_z(self, scale = False):
        return(self.Reader.GetZ(scale))
    def set_z(self, scale = False):
        return
    Z = property(get_z, set_z, None, None)
    z = Z

    def get_intensity(self):
        return(self.Reader.GetIntensity())
    def set_intensity(self):
        return
    
    intensity = property(get_intensity, set_intensity, None, None)
    Intensity = intensity

    def get_flag_byte(self):
        return(self.Reader.GetFlagByte())
    def set_flag_byte(self):
        return
    
    flag_byte = property(get_flag_byte, set_flag_byte, None, None)
    
    def get_return_num(self):
        return(self.Reader.GetReturnNum())
    def set_return_num(self):
        return

    return_num = property(get_return_num, set_return_num, None, None)

    def get_num_returns(self):
        return(self.Reader.GetNumReturns())
    def set_num_returns(self):
        return

    num_returns = property(get_return_num, set_num_returns, None, None)

    def get_scan_dir_flag(self):
        return(self.Reader.GetNumReturns())
    def set_scan_dir_flag(self):
        return

    scan_dir_flag = property(get_scan_dir_flag, set_scan_dir_flag, None, None)

    def get_scan_dir_flag(self):
        return(self.Reader.GetScanDirFlag())
    def set_scan_dir_flag(self):
        return

    scan_dir_flag = property(get_scan_dir_flag, set_scan_dir_flag, None, None)

    def get_edge_flight_line(self):
        return(self.Reader.GetEdgeFlightLine)
    def set_edge_flight_line(self):
        return

    edge_flight_line = property(get_edge_flight_line,
                                set_edge_flight_line, None, None)

    def get_raw_classification(self):
        return(self.Reader.GetClassification())
    def set_raw_classification(self):
        return
    raw_classification = property(get_raw_classification, 
                                  set_raw_classification, None, None)
    Raw_Classification = raw_classification

    def get_classification(self):
        return(self.Reader.GetClassification())
    def set_classification(self):
        return
    classification = property(get_classification, 
                              set_classification, None, None)
    Classification = classification

    def get_synthetic(self):
        return(self.Reader.GetSynthetic())
    def set_synthetic(self):
        return
    synthetic = property(get_synthetic, set_synthetic, None, None)
    Synthetic = synthetic 

    def get_key_point(self):
        return(self.Reader.GetKeyPoint())
    def set_key_point(self):
        return(self.Reader.SetKeyPoint())
    key_point = property(get_key_point, set_key_point, None, None)
    Key_Point = key_point

    def get_withheld(self):
        return(self.Reader.GetWithheld())
    def set_withheld(self):
        return
    withheld = property(get_withheld, set_withheld, None, None)
    Withheld = withheld

    def get_scan_angle_rank(self):
        return(self.Reader.GetScanAngleRank())
    def set_scan_angle_rank(self):
        return

    scan_angle_rank = property(get_scan_angle_rank, set_scan_angle_rank,None,None)

    def get_user_data(self):
        return(self.Reader.GetUserData())
    def set_user_data(self):
        return

    user_data = property(get_user_data, set_user_data, None, None)

    def get_pt_src_id(self):
        return(self.Reader.GetPTSrcId())
    def set_pt_src_id(self):
        pass

    pt_src_id = property(get_pt_src_id, set_pt_src_id, None, None)

    def get_gps_time(self):
        return(self.Reader.GetGPSTime())
    def set_gps_time(self):
        return
    
    gps_time = property(get_gps_time, set_gps_time, None, None)

    def get_red(self):
        return(self.Reader.GetRed())
    def set_red(self):
        return
    red = property(get_red, set_red, None, None)
    Red = red

    def get_green(self):
        return(self.Reader.GetGreen())
    def set_green(self):
        return
    
    green = property(get_green, set_green, None, None)
    Green = green

    def get_blue(self):
        return(self.Reader.GetBlue())
    def set_blue(self):
        return

    blue = property(get_blue, set_blue)
    Blue = blue

    def get_wave_packet_desc_index(self):
        return(self.Reader.GetWavePacketDescpIdx())
    def set_wave_packet_desc_index(self):
        return

    wave_packet_desc_index = property(get_wave_packet_desc_index,
                                      set_wave_packet_desc_index, None, None)
    
    def get_byte_offset_to_waveform_data(self):
        return(self.Reader.GetByteOffsetToWaveFmData())
    def set_byte_offset_to_waveform_data(self):
        return

    byte_offset_to_waveform_data = property(get_byte_offset_to_waveform_data,
                                            set_byte_offset_to_waveform_data,
                                            None, None)
    
    def get_waveform_packet_size(self):
        return(self.Reader.GetWavefmPktSize())
    def set_waveform_packet_size(self):
        return

    waveform_packet_size = property(get_waveform_packet_size, 
                                    set_waveform_packet_size, 
                                    None, None)
    
    def get_x_t(self):
        return(self.Reader.GetX_t())
    def set_x_t(self):
        return

    x_t = property(get_x_t, set_x_t, None, None)

    def get_y_t(self):
        return(self.Reader.GetY_t())
    def set_y_t(self):
        return
    
    y_t = property(get_y_t, set_y_t, None, None)

    def get_z_t(self):
        return(self.Reader.GetZ_t())
    def set_z_t(self):
        return

    z_t = property(get_z_t, set_z_t, None, None)


    
    




    def __iter__(self):
        """Iterator support (read mode only)

          >>> points = []
          >>> for i in f:
          ...   points.append(i)
          ...   print i # doctest: +ELLIPSIS
          <liblas.point.Point object at ...>
        """
        if self.mode == 0:
            self.at_end = False
            p = self.Reader.GetPoint(0)
            while p and not self.at_end:
                
                yield p
                p = self.Reader.GetNextPoint(self.handle)
                if not p:
                    self.at_end = True
            else:
                self.close()
                self.open()


    ### END OF GB REVISIONS ###

    def __getitem__(self, index):
        """Index and slicing support

          >>> out = f[0:3]
          [<liblas.point.Point object at ...>,
          <liblas.point.Point object at ...>,
          <liblas.point.Point object at ...>]
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
        :type pt: :obj:`liblas.point.Point` instance to write

        .. note::
            At this time, it is not possible to duck-type point objects and
            have them be written into the LAS file (from say numpy or
            something). You have to take care of this adaptation yourself.

        """
        if not isinstance(pt, point.Point):
            raise Exception('cannot write %s, it must '
                                    'be of type liblas.point.Point' % pt)
        if self.mode == 1 or self.mode == 2:
            #core.las.LASWriter_WritePoint(self.handle, pt.handle)
            pass

    def get_xmlsummary(self):
        """Returns an XML string summarizing all of the points in the reader
        
        .. note::
            This method will reset the reader's read position to the 0th 
            point to summarize the entire file, and it will again reset the 
            read position to the 0th point upon completion."""
        if self.mode != 0:
            raise Exception("file must be in read mode, not append or write mode to provide xml summary")
        return
        
    summary = property(get_xmlsummary, None, None, None)

if __name__ == "__main__":
    if (len(sys.argv)==2):
        LasFile = File(sys.argv[1])
        print(LasFile.header.get_pointrecordscount())
        print("Getting X")
        X = LasFile.X
        print("Getting Y")
        Y = LasFile.Y
        print("Getting Z")
        Z = LasFile.Z
        print("Getting Intensity")
        intensity = LasFile.intensity
        print("Getting Flag")
        flag_byte = LasFile.flag_byte
        print("Getting Raw Classification")
        raw_classification = LasFile.raw_classification
        print("Getting Classification")
        classification = LasFile.classification
        print("Getting Synthetic")
        synthetic = LasFile.synthetic
        print("Getting Key Point")
        key_point = LasFile.key_point
        print("Getting Withheld")
        withheld = LasFile.key_point
        print("Getting Scan Angle Rank")
        scan_angle_rank = LasFile.scan_angle_rank
        print("Gettng User Data")
        user_data = LasFile.user_data
        print("Getting Pt Src Id")
        pt_src_id = LasFile.pt_src_id
        if LasFile._header.PtDatFormatID in (1,2,3,4,5):
            print("Getting GPS Time")
            gps_time = LasFile.gps_time
        if LasFile._header.PtDatFormatID in (2,3,5):
            print("Getting Red")
            red = LasFile.red
            print("Getting Green")
            green = LasFile.green
            print("Getting Blue")
            blue = LasFile.blue
        if LasFile._header.PtDatFormatID in (4,5):
            print("Getting Wave Packet Descr Index")
            wave_form_packet_Desc_index = LasFile.wave_packet_desc_index
            print("Getting Byte Offset to Waveform")
            byte_offset_to_waveform = LasFile.byte_offset_to_waveform
            print("Getting Waveform Packet Size")
            waveform_packet_size = LasFile.waveform_packet_size
            print("Getting X(t)")
            x_t = LasFile.x_t
            print("Getting Y(t)")
            y_t = LasFile.y_t
            print("Getting Z(t)")
            z_t = LasFile.z_t
            
                        
        
        if ("simple.las" in sys.argv[1]):
            print("Tests, Looking at Points 100 and 976")
            
            idx1 = 100
            idx2 = 976
            p1 = LasFile.read(idx1)
            p2 = LasFile.read(idx2)
            print("Comparing X Y Z")
            assert(p1.X == 63666106 == X[idx1])
            assert(p1.Y == 84985413 == Y[idx1])
            assert(p1.Z == 42490 == Z[idx1])

            assert(p2.X == 63714022 == X[idx2])
            assert(p2.Y == 85318232 == Y[idx2])
            assert(p2.Z == 42306 == Z[idx2])
            print("...Passed")
            print("Comparing Intensity:")
            assert(p1.Intensity == 233 == intensity[idx1])
            assert(p2.Intensity == 1 == intensity[idx2])
            print("...Passed")
            print("Comparing Scan Angle Rank")
            assert(p1.ScanAngleRnk == 2 == scan_angle_rank[idx1])
            assert(p2.ScanAngleRnk == 12 == scan_angle_rank[idx2]) 
            print("...Passed")
            #print("Comparing Classification")
            #assert(p1.Classification == 1 == classification[idx1])
            #assert(p2.Classification == 2 == classification[idx2])
            #print("...Passed")
            print("Comparing Point Source ID")
            assert(p1.PtSrcID == 7328 == pt_src_id[idx1])
            assert(p2.PtSrcID == 7334 == pt_src_id[idx2])
            print("...Passed")
            print("Comparing GPS Time")
            assert(p1.GPSTime - 2*246504.221932 + gps_time[idx1] < 0.00001)
            assert(p2.GPSTime - 2*249774.658254 + gps_time[idx2] < 0.00001)
            print("...Passed")
            print("Comparing Red")
            assert(p1.Red == 92 == red[idx1])
            assert(p2.Red == 94 == red[idx2])
            print("...Passed")
            print("Comparing Green")
            assert(p1.Green == 100 == green[idx1])
            assert(p2.Green == 84 == green[idx2])
            print("...Passed")
            print("Comparing Blue")
            assert(p1.Blue == 110 == blue[idx1])
            assert(p2.Blue == 94 == blue[idx2])
            print("...Passed")
            
        
         
    else:
        print("You're clearly doing something wrong.")

