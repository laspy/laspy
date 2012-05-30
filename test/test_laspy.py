from laspy.base import *
import laspy.file as File
import laspy.header as lasheader

import unittest
import os

def flip_bit(x):
    return(1*(x==0))


class LasReaderTestCase(unittest.TestCase):
    simple = "./test/data/simple.las"
    def setUp(self): 
        inFile = open(self.simple, "r")
        inData = inFile.read()
        outFile = open("./.temp.las", "w")
        outFile.write(inData)
        outFile.close()
        inFile.close()
        self.FileObject = File.File("./.temp.las")
        LasFile = self.FileObject

        self.X = LasFile.X
        self.Y = LasFile.Y
        self.Z = LasFile.Z
        self.intensity = LasFile.intensity
        self.flag_byte = LasFile.flag_byte
        self.return_num = LasFile.return_num
        self.num_returns = LasFile.num_returns
        self.scan_dir_flag = LasFile.scan_dir_flag
        self.edge_flight_line = LasFile.edge_flight_line
        self.raw_classification = LasFile.raw_classification
        self.classification = LasFile.classification
        self.synthetic = LasFile.synthetic
        self.key_point = LasFile.key_point
        self.withheld = LasFile.key_point
        self.scan_angle_rank = LasFile.scan_angle_rank
        self.user_data = LasFile.user_data
        self.pt_src_id = LasFile.pt_src_id
        ## The following conditional code is redundant for 
        ## simple.las, which of course has only one pt. format.
        ## Perhaps find several other files?
        if LasFile._header.pt_dat_format_id in (1,2,3,4,5):
            self.gps_time = LasFile.gps_time
        if LasFile._header.pt_dat_format_id in (2,3,5):
            self.red = LasFile.red
            self.green = LasFile.green
            self.blue = LasFile.blue
        if LasFile._header.pt_dat_format_id in (4,5):
            self.wave_form_packet_Desc_index = LasFile.wave_packet_desc_index
            self.byte_offset_to_waveform = LasFile.byte_offset_to_waveform
            self.waveform_packet_size = LasFile.waveform_packet_size
            self.return_pt_waveform_loc = LasFile.return_pt_waveform_loc
            self.x_t = LasFile.x_t
            self.y_t = LasFile.y_t 
            self.z_t = LasFile.z_t

        self.p1 = LasFile.read(100)
        self.p2 = LasFile.read(976)

        self.idx1 = 100
        self.idx2 = 976


    def test_x(self):
        '''Fetch and test X dimension'''
        self.assertEqual(self.p1.X , 63666106 , self.X[self.idx1])
        self.assertEqual(self.p2.X , 63714022 , self.X[self.idx2])

    def test_y(self):
        '''Fetch and test Y dimension'''
        self.assertEqual(self.p1.Y , 84985413 , self.Y[self.idx1])
        self.assertEqual(self.p2.Y , 85318232 , self.Y[self.idx2])
        
    def test_z(self):
        '''Fetch and test Z dimension'''
        self.assertEqual(self.p1.Z , 42490 , self.Z[self.idx1])
        self.assertEqual(self.p2.Z , 42306 , self.Z[self.idx2])
        
        
    def test_intensity(self):
        '''Fetch and test intensity dimension'''
        self.assertEqual(self.p1.intensity , 233 ,
             self.intensity[self.idx1])
        self.assertEqual(self.p2.intensity , 1 , 
            self.intensity[self.idx2])
     
    
    def test_bit_flags(self):
        '''Fetch and test the binary flags associated with flag_byte dimension'''
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
        '''Fetch and test scan_angle_rank dimension'''
        self.assertEqual(self.p1.scan_angle_rank , 2 , 
            self.scan_angle_rank[self.idx1])
        self.assertEqual(self.p2.scan_angle_rank , 12 , 
            self.scan_angle_rank[self.idx2]) 
 

    def test_raw_classification(self):
        '''Fetch and test the dimension of raw_classification bytes'''
        self.assertEqual(self.p1.raw_classification , 1 , 
                self.raw_classification[self.idx1])
        self.assertEqual(self.p2.raw_classification , 2 , 
                 self.raw_classification[self.idx2])


    def test_ptstrcid(self):
        '''Fetch and test pt_src_id dimension'''
        self.assertEqual(self.p1.pt_src_id , 7328 , 
            self.pt_src_id[self.idx1])
        self.assertEqual(self.p2.pt_src_id , 7334 , 
            self.pt_src_id[self.idx2])


    def test_GPSTime(self):
        '''Fetch and test gps_time dimension'''
        self.assertTrue(self.p1.gps_time - 2*246504.221932 
                    + self.gps_time[self.idx1] < 0.00001)
        self.assertTrue(self.p2.gps_time - 2*249774.658254 
                    + self.gps_time[self.idx2] < 0.00001)


    def test_red(self):
        '''Fetch and test red dimension'''
        self.assertEqual(self.p1.red , 92 , self.red[self.idx1])
        self.assertEqual(self.p2.red , 94 , self.red[self.idx2])


    def test_green(self):
        '''Fetch and test green dimension'''
        self.assertEqual(self.p1.green , 100 , self.green[self.idx1])
        self.assertEqual(self.p2.green , 84 , self.green[self.idx2])


    def test_blue(self):
        '''Fetch and test blue dimension'''
        self.assertEqual(self.p1.blue , 110 , self.blue[self.idx1])
        self.assertEqual(self.p2.blue , 94 , self.blue[self.idx2])
        
    def test_iterator_and_slicing(self):
        '''Test iteraton and slicing over File objects'''     
        k = 0
        LasFile = self.FileObject
        for pt1 in LasFile:
            pt2 = LasFile[k]
            self.assertEqual(pt1.X, pt2.X)
            self.assertEqual(pt1.Y, pt2.Y)
            self.assertEqual(pt1.Z, pt2.Z)
            self.assertEqual(pt1.gps_time, pt2.gps_time)
            k += 1

    def tearDown(self): 
        self.FileObject.close() 
        os.remove("./.temp.las")      
        

class LasWriterTestCase(unittest.TestCase):
    simple = './test/data/simple.las'
    def setUp(self):
        inFile = open(self.simple, "r")
        inData = inFile.read()
        outFile = open("./.temp.las", "w")
        outFile.write(inData)
        outFile.close()
        inFile.close()
        self.FileObject = File.File("./.temp.las", mode = "w")
    
    def test_x(self):
        '''Writing and testing X dimenson'''
        x = self.FileObject.X + 1
        self.FileObject.X = x
        x2 = self.FileObject.get_x()         
        self.assertTrue(all(x == x2))        
    def test_y(self):
        '''Writing and testing Y dimension'''
        y = self.FileObject.Y + 1
        self.FileObject.Y = y
        y2 = self.FileObject.get_y()        
        self.assertTrue(all(y == y2))
    def test_z(self):
        '''Writing and testing Z dimension'''
        z = self.FileObject.Z + 1
        self.FileObject.Z = z
        z2 = self.FileObject.get_z()
        self.assertTrue(all(z == z2))
    def test_intensity(self):
        '''Writing and testing intensity dimension'''
        i = self.FileObject.intensity + 1
        self.FileObject.intensity = i
        i2 = self.FileObject.intensity
        self.assertTrue(all(i == i2))
    def test_return_num(self):
        '''Writing and testing return_num dimension'''
        rn = self.FileObject.return_num + 1
        self.FileObject.return_num = rn
        rn2 = self.FileObject.get_return_num()
        self.assertTrue(all(rn == rn2))
    def test_overflow_return_num(self):
        '''Testing overflow handling'''
        rn = self.FileObject.return_num + 100000
        with self.assertRaises(Exception):
            self.FileObject.return_num = rn
    def test_num_returns(self):
        '''Writing and testing num_returns dimension'''
        nr = self.FileObject.num_returns + 1
        self.FileObject.num_returns = nr
        nr2 = self.FileObject.get_num_returns()
        self.assertTrue(all(nr == nr2))
    def test_scan_dir_flag(self):
        '''Writing and testing scan_dir_flag dimension'''
        vf = np.vectorize(flip_bit) 
        sdf = vf(self.FileObject.scan_dir_flag)
        self.FileObject.scan_dir_flag = sdf
        sdf2 = self.FileObject.get_scan_dir_flag()
        self.assertTrue(all(sdf == sdf2))
    def test_edge_flight_line(self):
        '''Writing and testing edge_flight_line dimension'''
        vf = np.vectorize(flip_bit)
        efl = vf(self.FileObject.edge_flight_line)
        self.FileObject.edge_flight_line = efl
        efl2 = self.FileObject.get_edge_flight_line()
        self.assertTrue(all(efl == efl2))
    def test_classification(self):
        c1 = self.FileObject.classification + 1
        self.FileObject.classification = c1
        c2 = self.FileObject.get_classification()
        self.assertTrue(all(c1 == c2))
    def test_synthetic(self):
        vf = np.vectorize(flip_bit)   
        s1 = vf(self.FileObject.synthetic)
        self.FileObject.synthetic = s1 
        s2 = self.FileObject.get_synthetic()
        self.assertTrue(all(s1 == s2))
    def test_key_point(self):
        vf = np.vectorize(flip_bit)
        k1 = vf(self.FileObject.key_point)
        self.FileObject.key_point = k1
        k2 = self.FileObject.get_key_point()
        self.assertTrue(all(k1 == k2))
    def test_withheld(self):
        vf = np.vectorize(flip_bit)
        w1 = vf(self.FileObject.withheld)
        self.FileObject.withheld = w1
        w2 = self.FileObject.get_withheld()
        self.assertTrue(all(w1 == w2))
    def test_scan_angle_rank(self):
        ar1 = self.FileObject.scan_angle_rank - 1
        ar1 = [max(0, x) for x in ar1]
        self.FileObject.scan_angle_rank = ar1
        ar2 = self.FileObject.get_scan_angle_rank()
        self.assertTrue(all(ar1 == ar2))
    def test_user_data(self):
        ud1 = self.FileObject.user_data + 1
        self.FileObject.user_data = ud1
        ud2 = self.FileObject.get_user_data()
        self.assertTrue(all(ud1 == ud2))
    def test_pt_src_id(self):
        p1 = self.FileObject.user_data + 1
        self.FileObject.user_data = p1
        p2 = self.FileObject.get_user_data()
        self.assertTrue(all(p1 == p2))
    def test_gps_time(self):
        g1 = self.FileObject.gps_time + 0.1
        self.FileObject.gps_time = g1
        g2 = self.FileObject.get_gps_time()
        self.assertTrue(all(g1 == g2))
    def test_red(self):
        r1 = self.FileObject.red + 1
        self.FileObject.red = r1
        r2 = self.FileObject.get_red()
        self.assertTrue(all(r1 == r2))
    def test_green(self):
        g1 = self.FileObject.green + 1
        self.FileObject.green = g1
        g2 = self.FileObject.get_green()
        self.assertTrue(all(g1 == g2))
    def test_blue(self):
        b1 = self.FileObject.blue + 1
        self.FileObject.blue = b1
        b2 = self.FileObject.get_blue()
        self.assertTrue(all(b1 == b2))
    #def test_wave_pkt_descp_idx(self):
    #    w1 = self.FileObject.wave_packet_descp_idx + 1
    #    self.FileObject.wave_packet_descp_idx = w1
    #    w2 = self.FileObject.get_wave_packet_descp_idx()
    #    self.assertTrue(all(w1 = w2))
    #def test_byte_offset(self):
    #    b1 = self.FileObject.byte_offset_to_waveform_data + 1
    #    self.FileObject.byte_offset_to_waveform_data = b1
    #    b2 = self.FileObject.get_byte_offset_to_waveform_data
    #    self.assertTrue(all(b1 == b2))
    #def test_wavefm_pkt_size(self):
    #    w1 = self.FileObject.waveform_pkt_size + 1
    #    self.FileObject.waveform_pkt_size = w1
    #    w2 = self.FileObject.get_waveform_pkt_size()
    #    self.assertTrue(all(w1 == w2))
    #def test_return_pt_wavefm_loc(self):
    #    w1 = self.FileObject.return_pt_waveform_loc + 1
    #    self.FileObject.return_pt_waveform_loc = w1
    #    w2 = self.FileObject.get_return_pt_waveform_loc
    #    self.assertTrue(all(w1 == w2))
    #def test_x_t(self):
    #    x1 = self.FileObject.x_t + 1
    #    self.FileObject.x_t = x1
    #    x2 = self.FileObject.get_x_t()
    #    self.assertTrue(all(x1 == x2))
    #def test_y_t(self):
    #    y1 = self.FileObject.y_t + 1
    #    self.FileObject.y_t = y1
    #    y2 = self.FileObject.get_y_t()
    #    self.assertTrue(all(y1 == y2))
    #def test_z_t(self):
    #    z1 = self.FileObject.z_t + 1
    #    self.FileObject.z_t = z
    #    z2 = self.FileObject.get_z_t()
    #    self.assertTrue(all(z1 == z2))

        
        
        
    
    def tearDown(self):
        self.FileObject.close()
        os.remove("./.temp.las")


def test_laspy():
    reader = unittest.TestLoader().loadTestsFromTestCase(LasReaderTestCase)
    writer = unittest.TestLoader().loadTestsFromTestCase(LasWriterTestCase)
    return unittest.TestSuite([reader, writer])

# if __name__=="__main__":
#     runner = unittest.TextTestRunner()
#     runner.run(test_laspy())
    
    # unittest.main()
