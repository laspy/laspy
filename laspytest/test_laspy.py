import laspy
from laspy.base import *
import laspy.file as File
import laspy.header as header
from uuid import UUID
import unittest
import os

import shutil
def flip_bit(x):
    return(1*(x==0))


class LasReaderTestCase(unittest.TestCase):
    simple = "./laspytest/data/simple.las"
    tempfile = "junk.las"
    def setUp(self): 
        shutil.copyfile(self.simple, self.tempfile)
        self.FileObject = File.File(self.tempfile)
        LasFile = self.FileObject
        self.X = list(LasFile.X)
        self.Y = list(LasFile.Y)
        self.Z = list(LasFile.Z)
        self.intensity = list(LasFile.intensity)
        self.flag_byte = list(LasFile.flag_byte)
        self.return_num = list(LasFile.return_num)
        self.num_returns = list(LasFile.num_returns)
        self.scan_dir_flag = list(LasFile.scan_dir_flag)
        self.edge_flight_line = list(LasFile.edge_flight_line)
        self.raw_classification = list(LasFile.raw_classification)
        self.classification = list(LasFile.classification)
        self.synthetic = list(LasFile.synthetic)
        self.key_point = list(LasFile.key_point)
        self.withheld = list(LasFile.key_point)
        self.scan_angle_rank = list(LasFile.scan_angle_rank)
        self.user_data = list(LasFile.user_data)
        self.pt_src_id = list(LasFile.pt_src_id)
        ## The following conditional code is redundant for 
        ## simple.las, which of course has only one pt. format.
        ## Perhaps find several other files?
        if LasFile._header.data_format_id in (1,2,3,4,5):
            self.gps_time = list(LasFile.gps_time)
        if LasFile._header.data_format_id in (2,3,5):
            self.red = list(LasFile.red)
            self.green = list(LasFile.green)
            self.blue = list(LasFile.blue)
        if LasFile._header.data_format_id in (4,5):
            self.wave_form_packet_Desc_index = list(LasFile.wave_packet_desc_index)
            self.byte_offset_to_waveform = list(LasFile.byte_offset_to_waveform)
            self.waveform_packet_size = list(LasFile.waveform_packet_size)
            self.return_point_waveform_loc = list(LasFile.return_point_waveform_loc)
            self.x_t = list(LasFile.x_t)
            self.y_t = list(LasFile.y_t )
            self.z_t = list(LasFile.z_t)

        self.p1 = LasFile.read(100)
        self.p2 = LasFile.read(976)

        self.idx1 = 100
        self.idx2 = 976


    def test_x(self):
        """Fetch and test X dimension"""
        self.assertEqual(self.p1.X , 63666106 , self.X[self.idx1])
        self.assertEqual(self.p2.X , 63714022 , self.X[self.idx2])

    def test_y(self):
        """Fetch and test Y dimension"""
        self.assertEqual(self.p1.Y , 84985413 , self.Y[self.idx1])
        self.assertEqual(self.p2.Y , 85318232 , self.Y[self.idx2])
        
    def test_z(self):
        """Fetch and test Z dimension"""
        self.assertEqual(self.p1.Z , 42490 , self.Z[self.idx1])
        self.assertEqual(self.p2.Z , 42306 , self.Z[self.idx2])
        
        
    def test_intensity(self):
        """Fetch and test intensity dimension"""
        self.assertEqual(self.p1.intensity , 233 ,
             self.intensity[self.idx1])
        self.assertEqual(self.p2.intensity , 1 , 
            self.intensity[self.idx2])
     
    
    def test_bit_flags(self):
        """Fetch and test the binary flags associated with flag_byte dimension"""
        self.assertEqual(self.p1.flag_byte , self.flag_byte[self.idx1])
        self.assertEqual(self.p2.flag_byte , self.flag_byte[self.idx2])
        self.assertEqual(self.p1.return_num , 
            self.return_num[self.idx1] , 1)
        self.assertEqual(self.p2.return_num , 
            self.return_num[self.idx2] , 2)
        self.assertEqual(self.p1.num_returns , 
            self.num_returns[self.idx1] , 1)
        self.assertEqual(self.p2.num_returns , 
            self.num_returns[self.idx2] , 2)
        self.assertEqual(self.p1.scan_dir_flag , 
            self.scan_dir_flag[self.idx1] , 0)
        self.assertEqual(self.p2.scan_dir_flag , 
            self.scan_dir_flag[self.idx2] , 1)
        self.assertEqual(self.p1.edge_flight_line , 
            self.edge_flight_line[self.idx1] , 0)
        self.assertEqual(self.p2.edge_flight_line , 
            self.edge_flight_line[self.idx2] , 0)
   
  
    def test_scan_angle_rank(self):
        """Fetch and test scan_angle_rank dimension"""
        self.assertEqual(self.p1.scan_angle_rank , 2 , 
            self.scan_angle_rank[self.idx1])
        self.assertEqual(self.p2.scan_angle_rank , 12 , 
            self.scan_angle_rank[self.idx2]) 
 

    def test_raw_classification(self):
        """Fetch and test the dimension of raw_classification bytes"""
        self.assertEqual(self.p1.raw_classification , 1 , 
                self.raw_classification[self.idx1])
        self.assertEqual(self.p2.raw_classification , 2 , 
                 self.raw_classification[self.idx2])


    def test_ptstrcid(self):
        """Fetch and test pt_src_id dimension"""
        self.assertEqual(self.p1.pt_src_id , 7328 , 
            self.pt_src_id[self.idx1])
        self.assertEqual(self.p2.pt_src_id , 7334 , 
            self.pt_src_id[self.idx2])


    def test_GPSTime(self):
        """Fetch and test gps_time dimension"""
        self.assertTrue(self.p1.gps_time - 2*246504.221932 
                    + self.gps_time[self.idx1] < 0.00001)
        self.assertTrue(self.p2.gps_time - 2*249774.658254 
                    + self.gps_time[self.idx2] < 0.00001)


    def test_red(self):
        """Fetch and test red dimension"""
        self.assertEqual(self.p1.red , 92 , self.red[self.idx1])
        self.assertEqual(self.p2.red , 94 , self.red[self.idx2])


    def test_green(self):
        """Fetch and test green dimension"""
        self.assertEqual(self.p1.green , 100 , self.green[self.idx1])
        self.assertEqual(self.p2.green , 84 , self.green[self.idx2])


    def test_blue(self):
        """Fetch and test blue dimension"""
        self.assertEqual(self.p1.blue , 110 , self.blue[self.idx1])
        self.assertEqual(self.p2.blue , 94 , self.blue[self.idx2])
        
    def test_iterator_and_slicing(self):
        """Test iteraton and slicing over File objects"""     
        k = 0
        LasFile = self.FileObject
        for pt1 in LasFile:
            pt2 = LasFile[k]
            pt1.make_nice()
            pt2.make_nice() 
            self.assertEqual(pt1.X, pt2.X)
            self.assertEqual(pt1.Y, pt2.Y)
            self.assertEqual(pt1.Z, pt2.Z)
            self.assertEqual(pt1.gps_time, pt2.gps_time)
            k += 1
        with self.assertRaises(Exception):
            LasFile[10000]

    def tearDown(self): 
        self.FileObject.close() 
        os.remove(self.tempfile)      
        

class LasWriterTestCase(unittest.TestCase):
    simple = './laspytest/data/simple.las'
    tempfile = 'writer.las'
    output_tempfile = 'writer_output.las'
    def setUp(self):
        shutil.copyfile(self.simple, self.tempfile)  
        self.FileObject = File.File(self.tempfile, mode = "rw")
    
    def test_x(self):
        """Writing and testing X dimenson"""
        x = [i + 1 for i in self.FileObject.X]
        self.FileObject.X = x
        x2 = self.FileObject.get_x()         
        self.assertTrue((list(x) == list(x2)))        
        scaled_x = self.FileObject.x
        self.FileObject.x = scaled_x
        self.assertTrue(all(scaled_x == self.FileObject.x))

    def test_y(self):
        """Writing and testing Y dimension"""
        y = [i + 1 for i in self.FileObject.Y] 
        self.FileObject.Y = y
        y2 = self.FileObject.get_y()        
        self.assertTrue((list(y) == list(y2)))
        scaled_y = self.FileObject.y
        self.FileObject.y = scaled_y
        self.assertTrue(all(scaled_y == self.FileObject.y))

    def test_z(self):
        """Writing and testing Z dimension"""
        z = [i + 1 for i in self.FileObject.Z ]
        self.FileObject.Z = z
        z2 = self.FileObject.get_z()
        self.assertTrue((list(z) == list(z2)))
        scaled_z = self.FileObject.z
        self.FileObject.z = scaled_z
        self.assertTrue(all(scaled_z == self.FileObject.z))

    def test_intensity(self):
        """Writing and testing intensity dimension"""
        i = [i + 1 for i in self.FileObject.intensity]
        self.FileObject.intensity = i
        i2 = self.FileObject.intensity
        self.assertTrue((i == list(i2)))
    def test_return_num(self):
        """Writing and testing return_num dimension"""
        rn = [i + 1 for i in self.FileObject.return_num]
        self.FileObject.return_num = rn
        rn2 = self.FileObject.get_return_num()
        self.assertTrue((rn == list(rn2)))
    def test_overflow_return_num(self):
        """Testing overflow handling"""
        rn = [x + 100000 for x in self.FileObject.return_num]
        with self.assertRaises(Exception):
            self.FileObject.return_num = rn
    def test_num_returns(self):
        """Writing and testing num_returns dimension"""
        nr = [i + 1 for i in self.FileObject.num_returns]
        self.FileObject.num_returns = nr
        nr2 = self.FileObject.get_num_returns()
        self.assertTrue((nr == list(nr2)))
    def test_scan_dir_flag(self):
        """Writing and testing scan_dir_flag dimension"""
        sdf = [flip_bit(x) for x in self.FileObject.scan_dir_flag]
        self.FileObject.scan_dir_flag = sdf
        sdf2 = self.FileObject.get_scan_dir_flag()
        self.assertTrue((sdf == list(sdf2)))
    def test_edge_flight_line(self):
        """Writing and testing edge_flight_line dimension"""
        efl = [flip_bit(x) for x in self.FileObject.edge_flight_line] 
        self.FileObject.edge_flight_line = efl
        efl2 = self.FileObject.get_edge_flight_line()
        self.assertTrue((efl == list(efl2)))
    def test_classification(self):
        """Writing and testing classification byte."""
        c1 = [x + 1 for x in self.FileObject.classification]
        self.FileObject.classification = c1
        c2 = [x for x in self.FileObject.get_classification()]
        self.assertTrue((c1 == c2))
    def test_synthetic(self):
        """Writing and testing synthetic"""
        s1 = [flip_bit(x) for x in self.FileObject.synthetic]  
        self.FileObject.synthetic = s1 
        s2 = self.FileObject.get_synthetic()
        self.assertTrue((s1 == list(s2)))
    def test_key_point(self):
        """Writing and testing key point"""
        k1 = [flip_bit(x) for x in self.FileObject.key_point] 
        self.FileObject.key_point = k1
        k2 = self.FileObject.get_key_point()
        self.assertTrue((k1 == list(k2)))
    def test_withheld(self):
        """Writing and testing withheld"""
        w1 = [flip_bit(x) for x in self.FileObject.withheld] 
        self.FileObject.withheld = w1
        w2 = self.FileObject.get_withheld()
        self.assertTrue((w1 == list(w2)))
    def test_scan_angle_rank(self):
        """Writing and testing scan angle rank"""
        ar1 = [i-1 for i in self.FileObject.scan_angle_rank]
        ar1 = [max(0, x) for x in ar1]
        self.FileObject.scan_angle_rank = ar1
        ar2 = self.FileObject.get_scan_angle_rank()
        self.assertTrue((ar1 == list(ar2)))
    def test_user_data(self):
        """Writing and testing user data"""
        ud1 = [i+1 for i in self.FileObject.user_data]
        self.FileObject.user_data = ud1
        ud2 = self.FileObject.get_user_data()
        self.assertTrue((ud1 == list(ud2)))
    def test_pt_src_id(self):
        """Writing and testing point source id"""
        p1 = [i+1 for i in self.FileObject.user_data]
        self.FileObject.user_data = p1
        p2 = self.FileObject.get_user_data()
        self.assertTrue((p1 == list(p2)))
    def test_gps_time(self):
        """Writing and testing gps time"""
        g1 = [i+1 for i in self.FileObject.gps_time]
        self.FileObject.gps_time = g1
        g2 = self.FileObject.get_gps_time()
        self.assertTrue((g1 == list(g2)))
    def test_red(self):
        """Writing and testing red"""
        r1 = [i+1 for i in self.FileObject.red]
        self.FileObject.red = r1
        r2 = self.FileObject.get_red()
        self.assertTrue((r1 == list(r2)))
    def test_green(self):
        """Writing and testing green"""
        g1 = [i+1 for i in self.FileObject.green]
        self.FileObject.green = g1
        g2 = self.FileObject.get_green()
        self.assertTrue((g1 == list(g2)))
    def test_blue(self):
        """Writing and testing blue"""
        b1 =[i+1 for i in  self.FileObject.blue]
        self.FileObject.blue = b1
        b2 = self.FileObject.get_blue()
        self.assertTrue((b1 == list(b2)))
    def test_vlr_defined_dimensions2(self):
        """Testing VLR defined dimension API"""
        File2 = File.File(self.output_tempfile, mode = "w", header = self.FileObject.header)
        File2.define_new_dimension("test_dimension", 5, "This is a test.")
        File2.X = self.FileObject.X
        self.assertTrue(File2.test_dimension[500] == 0)
        File2.close(ignore_header_changes = True)
    #def test_wave_pkt_descp_idx(self):
    #    w1 = self.FileObject.wave_packet_descp_idx + 1
    #    self.FileObject.wave_packet_descp_idx = w1
    #    w2 = self.FileObject.get_wave_packet_descp_idx()
    #    self.assertTrue((w1 = w2))
    #def test_byte_offset(self):
    #    b1 = self.FileObject.byte_offset_to_waveform_data + 1
    #    self.FileObject.byte_offset_to_waveform_data = b1
    #    b2 = self.FileObject.get_byte_offset_to_waveform_data
    #    self.assertTrue((b1 == b2))
    #def test_wavefm_pkt_size(self):
    #    w1 = self.FileObject.waveform_pkt_size + 1
    #    self.FileObject.waveform_pkt_size = w1
    #    w2 = self.FileObject.get_waveform_pkt_size()
    #    self.assertTrue((w1 == w2))
    #def test_return_pt_wavefm_loc(self):
    #    w1 = self.FileObject.return_point_waveform_loc + 1
    #    self.FileObject.return_point_waveform_loc = w1
    #    w2 = self.FileObject.get_return_point_waveform_loc
    #    self.assertTrue((w1 == w2))
    #def test_x_t(self):
    #    x1 = self.FileObject.x_t + 1
    #    self.FileObject.x_t = x1
    #    x2 = self.FileObject.get_x_t()
    #    self.assertTrue((x1 == x2))
    #def test_y_t(self):
    #    y1 = self.FileObject.y_t + 1
    #    self.FileObject.y_t = y1
    #    y2 = self.FileObject.get_y_t()
    #    self.assertTrue((y1 == y2))
    #def test_z_t(self):
    #    z1 = self.FileObject.z_t + 1
    #    self.FileObject.z_t = z
    #    z2 = self.FileObject.get_z_t()
    #    self.assertTrue((z1 == z2))    
    def tearDown(self):
        self.FileObject.close()
        os.remove(self.tempfile)

class LasHeaderWriterTestCase(unittest.TestCase):
    simple = os.path.abspath('./laspytest/data/simple.las')
    simple14 = os.path.abspath('./laspytest/data/simple1_4.las')
    tempfile = os.path.abspath('headerwriter.las')
    tempfile2 = os.path.abspath('headerwriter2.las')

    def setUp(self):
        shutil.copyfile(self.simple, self.tempfile)
        self.FileObject = File.File(self.tempfile, mode = "rw")

    def test_file_src(self):
        """Testing file_src"""
        f1 = self.FileObject.header.filesource_id + 1
        self.FileObject.header.filesource_id = f1
        f2 = self.FileObject.header.get_filesourceid()
        self.assertTrue(f1 == f2)  
    def test_uuid(self):
        """Testing uuid"""
        guid = self.FileObject.header.guid
        guid2 = self.FileObject.header.project_id
        self.assertEqual(guid, guid2)
        newGuid = UUID(bytes="1"*16)
        self.FileObject.header.guid = newGuid
        newGuid2 = self.FileObject.header.get_guid()
        self.assertEqual(newGuid, newGuid2)
    def test_glob_encode(self):
        """Testing Global Encoding"""
        g1 = self.FileObject.header.global_encoding + 1
        self.FileObject.header.global_encoding = g1
        g2 = self.FileObject.header.get_global_encoding()
        self.assertTrue(g1 == g2)
    def test_versions(self):
        """Testing Versions"""
        v1 = self.FileObject.header.major_version
        self.assertEqual(v1, 1)
        with self.assertRaises(laspy.util.LaspyException):
            self.FileObject.header.major_version = 2
    def test_system_id(self):
        """Testing System ID"""
        sys1 = self.FileObject.header.system_id
        sys1 = "1234567891" + sys1[10:]
        self.FileObject.header.system_id = sys1
        sys2 = self.FileObject.header.get_systemid()
        self.assertEqual(sys1, sys2)
    def test_software_id(self):
        """"Testing Software ID"""
        s1 = self.FileObject.header.software_id
        s1 = "1234567" + s1[7:]
        self.FileObject.header.software_id = s1
        s2 = self.FileObject.header.get_softwareid()
        self.assertEqual(s1, s2)
        with self.assertRaises(laspy.util.LaspyException):
            self.FileObject.header.software_id = "123"
        with self.assertRaises(laspy.util.LaspyException):
            self.FileObject.header.software_id = "1" * 100
    def test_padding(self):
        """Testing Padding"""
        x1 = list(self.FileObject.X)
        self.FileObject.header.set_padding(10)
        self.FileObject.header.set_padding(1000)
        x2 = list(self.FileObject.X)
        self.assertTrue((list(x1) == list(x2)))
    def test_data_offset(self):
        """Testing data offset"""
        x1 = list(self.FileObject.X )
        self.FileObject.header.data_offset = 400
        self.assertEqual(self.FileObject.header.get_dataoffset(), 400)
        x2 = list(self.FileObject.X)
        self.assertTrue((list(x1) == list(x2)))
    def test_date(self):
        """Testing Date"""
        d1 = self.FileObject.header.date
        self.assertTrue(d1 == None)
        from datetime import datetime
        d2 = datetime(2007,12,10)
        self.FileObject.header.date = d2
        d3 = self.FileObject.header.get_date()
        self.assertEqual(d2, d3)

    def test_point_recs_by_return(self):
        """Testing point records by return"""
        r1 = [x + 1 for x in self.FileObject.header.point_return_count]
        self.FileObject.header.point_return_count = r1
        r2 = self.FileObject.header.get_pointrecordsbyreturncount()
        self.assertTrue(r1 == r2)
    def test_min_max_update(self):
        """Testing the update min/max function"""
        x = list(self.FileObject.X)
        x[0] = max(x) + 1
        y = list(self.FileObject.Y)
        y[0] = max(y) + 1
        z = list(self.FileObject.Z)
        z[0] = max(z) + 1
        self.FileObject.X = x
        self.FileObject.Y = y
        self.FileObject.Z = z
        self.FileObject.header.update_min_max()
        file_max = self.FileObject.header.max
        self.assertTrue(file_max == [self.FileObject.x[0], self.FileObject.y[0], self.FileObject.z[0]])
    def test_histogram(self):
        """Testing the update_histogram functon"""
        h1 = self.FileObject.header.point_return_count
        self.FileObject.header.update_histogram()
        h2 = self.FileObject.header.point_return_count
        self.assertTrue(h1 == h2)
    def test_offset(self):
        """Testing offset"""
        o1 = self.FileObject.header.offset
        o1[0] += 1
        self.FileObject.header.offset = o1
        o2 = self.FileObject.header.get_offset()
        self.assertTrue(o1 == o2)
    def test_scale(self):
        """Testing Scale"""
        s1 = self.FileObject.header.scale
        s1[0] += 1
        self.FileObject.header.scale = s1
        s2 = list(self.FileObject.header.get_scale())
        self.assertTrue(s1 == s2)
    def test_vlr_parsing_api(self):
        """Testing VLR body parsing api"""
        shutil.copyfile(self.simple14, self.tempfile2)
        VLRFile = File.File(self.tempfile2, mode = "rw")
        vlr0 = VLRFile.header.vlrs[0]
        vlr0.parsed_body[-1] += 1
        pb = vlr0.parsed_body
        vlr0.pack_data()
        VLRFile.header.save_vlrs()
        VLRFile.close()
        
        VLRFile = File.File(self.tempfile2, mode = "rw")
        self.assertTrue(all(pb == VLRFile.header.vlrs[0].parsed_body))
        VLRFile.close() 

    def tearDown(self):
        self.FileObject.close()
        os.remove(self.tempfile)

class LasWriteModeTestCase(unittest.TestCase):
    simple = './laspytest/data/simple.las'
    tempfile = 'write-mode.las'
    output_tempfile = 'write-mode-output.las'
    def setUp(self):
        shutil.copyfile(self.simple, self.tempfile)  
        self.File1 = File.File(self.tempfile, mode = "r")

    def test_using_barebones_header(self):
        """Testing file creation using barebones header"""
        header_object = header.Header()

        File2 = File.File(self.output_tempfile, mode = "w", 
                            header = header_object)
        self.assertTrue(File2.header.version == "1.2") 

        X = list(self.File1.X)
        Y = list(self.File1.Y)
        Z = list(self.File1.Z)
        File2.X = X
        File2.Y = Y
        File2.Z = Z
        self.assertTrue((list(X) == list(File2.get_x())))
        self.assertTrue((list(Y) == list(File2.get_y())))
        self.assertTrue((list(Z) == list(File2.get_z())))
        File2.close(ignore_header_changes = True)

    def test_using_existing_header(self):
        """Test file creation using an existing header"""
        header_object = self.File1.header
        File2 = File.File(self.output_tempfile, mode = "w",
                            header = header_object)
        X = list(self.File1.X)
        Y = list(self.File1.Y)
        Z = list(self.File1.Z)
        File2.Z = Z
        File2.Y = Y
        File2.X = X
        self.assertTrue((list(X) == list(File2.get_x())))
        self.assertTrue((list(Y) == list(File2.get_y())))
        self.assertTrue((list(Z) == list(File2.get_z())))
        File2.close(ignore_header_changes = True)		

    def test_format_change_and_extra_bytes(self):
        """Testing format change and extra_bytes"""
        File1 = self.File1
        new_header = File1.header.copy()
        new_header.format = 1.2
        new_header.data_format_id = 0
        new_header.data_record_length = 50
       
        
        File2 = File.File(self.output_tempfile, mode = "w", 
                            header = new_header)
        for dim in File1.point_format:
            in_dim = File1.reader.get_dimension(dim.name)
            if dim.name in File2.point_format.lookup:
                File2.writer.set_dimension(dim.name, in_dim)
        File2.extra_bytes = ["Test"] * len(File2)

        self.assertTrue("Test" in str(File2.get_extra_bytes()[14]))
        File2.close(ignore_header_changes = True)
    def tearDown(self):
        self.File1.close()
        os.remove(self.tempfile)

class LasV_13TestCase(unittest.TestCase):
    simple = './laspytest/data/simple1_3.las'
    tempfile = 'v13.las'
    output_tempfile = 'v13-output.las'
    def setUp(self):
        shutil.copyfile(self.simple, self.tempfile)  
        self.File1 = File.File(self.tempfile, mode = "rw")

    def test_glob_encode(self):
        """Testing v1.3 Global Encoding"""
        old = self.File1.header.gps_time_type
        self.assertTrue(old == '0')
        self.File1.header.gps_time_type = '1'
        self.assertEqual(self.File1.header.get_gps_time_type(), '1')
        
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        self.assertEqual(self.File1.header.waveform_data_packets_internal,
                        File2.header.waveform_data_packets_internal)
        self.assertEqual(self.File1.header.waveform_data_packets_external,
                        File2.header.waveform_data_packets_external)
        self.assertEqual(self.File1.header.synthetic_return_num, 
                        File2.header.synthetic_return_num)
        File2.close(ignore_header_changes = True)    

    def test_evlr(self):
        """Testing v1.3 EVLR support."""
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        self.assertEqual(self.File1.header.evlrs[0].to_byte_string(),
                        File2.header.evlrs[0].to_byte_string())
        File2.close(ignore_header_changes = True)
    def test_wave_packet_desc_index(self):
        """Testing wave_packet_desc_index."""
        test1 = self.File1.wave_packet_desc_index 
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        File2.points = self.File1.points
        self.assertTrue(all(test1 == File2.wave_packet_desc_index))
        File2.wave_packet_desc_index += 1
        self.assertTrue(all(test1 != File2.wave_packet_desc_index))
        File2.close(ignore_header_changes = True)
    def test_byte_offset_to_waveform_data(self):
        """Testing byte_offset_to_waveform_data"""
        test1 = self.File1.byte_offset_to_waveform_data 
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        File2.points = self.File1.points
        self.assertTrue(all(test1 == File2.byte_offset_to_waveform_data))
        File2.byte_offset_to_waveform_data += 1
        self.assertTrue(all(test1 != File2.byte_offset_to_waveform_data))
        File2.close(ignore_header_changes = True)
    def test_waveform_packet_size(self):
        """Testing waveform_packet_size"""
        test1 = self.File1.waveform_packet_size 
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        File2.points = self.File1.points
        self.assertTrue(all(test1 == File2.waveform_packet_size))
        File2.waveform_packet_size += 1
        self.assertTrue(all(test1 != File2.waveform_packet_size))
        File2.close(ignore_header_changes = True)    
    def test_return_point_waveform_loc(self):
        """Testing return_point_waveform_loc"""
        test1 = self.File1.return_point_waveform_loc 
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        File2.points = self.File1.points
        self.assertTrue(all(test1 == File2.return_point_waveform_loc))
        File2.return_point_waveform_loc += 1
        self.assertTrue(all(test1 != File2.return_point_waveform_loc))
        File2.close(ignore_header_changes = True)
    def test_x_t(self):
        """Testing x_t"""
        test1 = self.File1.x_t 
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        File2.points = self.File1.points
        self.assertTrue(all(test1 == File2.x_t))
        File2.x_t += 1
        self.assertTrue(all(test1 != File2.x_t))
        File2.close(ignore_header_changes = True)
    def test_y_t(self):
        """Testing y_t"""
        test1 = self.File1.y_t 
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        File2.points = self.File1.points
        self.assertTrue(all(test1 == File2.y_t))
        File2.y_t += 1
        self.assertTrue(all(test1 != File2.y_t))
        File2.close(ignore_header_changes = True)
    def test_z_t(self):
        """Testing z_t"""
        test1 = self.File1.z_t 
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        File2.points = self.File1.points
        self.assertTrue(all(test1 == File2.z_t))
        File2.z_t += 1
        self.assertTrue(all(test1 != File2.z_t))
        File2.close(ignore_header_changes = True)

    def tearDown(self):
        self.File1.close()
        os.remove(self.tempfile)

class LasV_14TestCase(unittest.TestCase):
    simple = './laspytest/data/simple1_4.las'
    tempfile = 'v14.las'
    output_tempfile = 'v14-output.las'
    def setUp(self):
        shutil.copyfile(self.simple, self.tempfile)  
        self.File1 = File.File(self.tempfile, mode = "rw")

    def test_glob_encode(self):
        """Testing v1.4 Global Encoding"""
        old = self.File1.header.gps_time_type
        self.assertTrue(old == '0')
        self.File1.header.gps_time_type = '1'
        self.assertEqual(self.File1.header.get_gps_time_type(), '1')
        
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        self.assertEqual(self.File1.header.waveform_data_packets_internal,
                        File2.header.waveform_data_packets_internal)
        self.assertEqual(self.File1.header.waveform_data_packets_external,
                        File2.header.waveform_data_packets_external)
        self.assertEqual(self.File1.header.synthetic_return_num, 
                        File2.header.synthetic_return_num)
        File2.close(ignore_header_changes = True)    

    def test_glob_encode_bits(self):
        b1 = self.File1.header.gps_time_type
        b2 = self.File1.header.waveform_data_packets_internal
        b3 = self.File1.header.waveform_data_packets_external
        b4 = self.File1.header.synthetic_return_num
        b5 = self.File1.header.wkt

        bf1 = 1 - int(b1)
        bf2 = 1 - int(b2)
        bf3 = 1 - int(b3)
        bf4 = 1 - int(b4)
        bf5 = 1 - int(b5)

        self.File1.header.gps_time_type = bf1
        self.File1.header.waveform_data_packets_internal = bf2
        self.File1.header.waveform_data_packets_external = bf3
        self.File1.header.synthetic_return_num = bf4
        self.File1.header.wkt = bf5

        self.assertEqual(self.File1.header.gps_time_type, str(bf1))
        self.assertEqual(self.File1.header.waveform_data_packets_internal, str(bf2))
        self.assertEqual(self.File1.header.waveform_data_packets_external, str(bf3))
        self.assertEqual(self.File1.header.synthetic_return_num, str(bf4))
        self.assertEqual(self.File1.header.wkt, str(bf5))

    def test_evlr(self):
        """ Testing v1.4 EVLR support"""
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        self.assertEqual(self.File1.header.evlrs[0].to_byte_string(),
                        File2.header.evlrs[0].to_byte_string())
        File2.points = self.File1.points
        outevlrs = []
        [outevlrs.append(File2.header.evlrs[0]) for i in xrange(50)]
        File2.header.evlrs = outevlrs
        File2.close()
        File2 = File.File(self.output_tempfile, mode = "r")
        self.assertTrue(len(File2.header.evlrs) == 50)
        File2.close(ignore_header_changes = True)

    def test_classification_variables(self):
        """Testing v1.4 classification support"""
        classification = self.File1.classification
        classification_flags = self.File1.classification_flags
        scanner_channel = self.File1.scanner_channel
        scan_dir_flag = self.File1.scan_dir_flag
        edge_flight_line = self.File1.edge_flight_line

        return_num = self.File1.return_num
        num_returns = self.File1.num_returns
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        File2.classification = classification
        File2.classification_flags = classification_flags
        File2.scan_dir_flag = scan_dir_flag
        File2.scanner_channel = scanner_channel
        File2.edge_flight_line = edge_flight_line
        File2.return_num = return_num
        File2.num_returns = num_returns
        
        self.assertTrue(all(num_returns == File2.get_num_returns()))
        self.assertTrue(all(return_num == File2.get_return_num())) 
        self.assertTrue(all(edge_flight_line == File2.get_edge_flight_line())) 
        self.assertTrue(all(scan_dir_flag ==File2.get_scan_dir_flag() )) 
        self.assertTrue(all(classification_flags == File2.get_classification_flags())) 
        self.assertTrue(all(classification == File2.get_classification())) 
        self.assertTrue(all(scanner_channel == File2.get_scanner_channel()))
        File2.close(ignore_header_changes = True)

    def test_vlr_defined_dimensions(self):
        """Testing v1.4 VLR defined dimensions (LL API)"""
        new_header = self.File1.header.copy()
        # Test basic numeric dimension
        new_dim_record1 = header.ExtraBytesStruct(name = "Test Dimension 1234", data_type = 5) 
        # Test string dimension (len 3)
        new_dim_record2 = header.ExtraBytesStruct(name = "Test Dimension 5678", data_type = 22)
        # Test integer array dimension (len 3)
        new_dim_record3 = header.ExtraBytesStruct(name = "Test Dimension 9", data_type =  26) 
        new_VLR_rec = header.VLR(user_id = "LASF_Spec", record_id = 4, 
                VLR_body = (new_dim_record1.to_byte_string() + new_dim_record2.to_byte_string() + new_dim_record3.to_byte_string()))
        new_header.data_record_length += (19)
        File2 = File.File(self.output_tempfile, mode = "w", header = new_header, vlrs = [new_VLR_rec], evlrs = self.File1.header.evlrs)

        File2.X = self.File1.X

        File2._writer.set_dimension("test_dimension_1234", [4]*len(self.File1))
        File2._writer.set_dimension("test_dimension_5678", ["AAA"]*len(self.File1))
        File2._writer.set_dimension("test_dimension_9", [[1,2,3]]*len(self.File1))
        self.assertTrue(all(np.array(["AAA"]*len(self.File1)) == File2.test_dimension_5678))
        self.assertTrue(all(np.array([4]*len(self.File1)) == File2.test_dimension_1234))
        self.assertTrue(list(File2.test_dimension_9[100]) == [1,2,3])
        File2.close(ignore_header_changes = True)


    def test_vlr_defined_dimensions2(self):
        """Testing VLR defined dimensions (HL API)"""
        File2 = File.File(self.output_tempfile, mode = "w", header = self.File1.header)
        File2.define_new_dimension("test_dimension", 5, "This is a test.")
        File2.define_new_dimension("test_dimension2", 5, "This is a test.")

        File2.X = self.File1.X
        self.assertTrue(File2.test_dimension[500] == 0)
        self.assertTrue(File2.test_dimension2[123] == 0)
        File2.close(ignore_header_changes = True)

    def tearDown(self):
        self.File1.close()
        os.remove(self.tempfile)


class LasLazReaderTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_read_data(self):
        """Testing ability to read laz files."""
        simple = './laspytest/data/simple.laz'
        File1 = File.File(simple, mode = "r")
        self.assertTrue(len(File1.X) == 1065)
        File1.close()    

    def tearDown(self):
        pass 



def test_laspy():
    reader = unittest.TestLoader().loadTestsFromTestCase(LasReaderTestCase)
    writer = unittest.TestLoader().loadTestsFromTestCase(LasWriterTestCase)
    header_writer = unittest.TestLoader().loadTestsFromTestCase(LasHeaderWriterTestCase)
    write_mode = unittest.TestLoader().loadTestsFromTestCase(LasWriteModeTestCase)
    las13 = unittest.TestLoader().loadTestsFromTestCase(LasV_13TestCase)
    las14 = unittest.TestLoader().loadTestsFromTestCase(LasV_14TestCase)
    #laz = unittest.TestLoader().loadTestsFromTestCase(LasLazReaderTestCase)

    return unittest.TestSuite([reader, writer, header_writer, write_mode, 
        las13, las14])

