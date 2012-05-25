from base import *
import file as File
import header as lasheader
import unittest
import os

class LasReaderTestCase(unittest.TestCase):
    def setUp(self): 
        inFile = open("../simple.las", "r")
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
        if LasFile._header.PtDatFormatID in (1,2,3,4,5):
            self.gps_time = LasFile.gps_time
        if LasFile._header.PtDatFormatID in (2,3,5):
            self.red = LasFile.red
            self.green = LasFile.green
            self.blue = LasFile.blue
        if LasFile._header.PtDatFormatID in (4,5):
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
        self.assertEqual(self.p1.X , 63666106 , self.X[self.idx1])
        self.assertEqual(self.p2.X , 63714022 , self.X[self.idx2])

    def test_y(self):
        self.assertEqual(self.p1.Y , 84985413 , self.Y[self.idx1])
        self.assertEqual(self.p2.Y , 85318232 , self.Y[self.idx2])
        
    def test_z(self):
        self.assertEqual(self.p1.Z , 42490 , self.Z[self.idx1])
        self.assertEqual(self.p2.Z , 42306 , self.Z[self.idx2])
        
        
    def test_intensity(self):
        self.assertEqual(self.p1.intensity , 233 ,
             self.intensity[self.idx1])
        self.assertEqual(self.p2.intensity , 1 , 
            self.intensity[self.idx2])
     
    
    def test_bit_flags(self):
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
        self.assertEqual(self.p1.scan_angle_rank , 2 , 
            self.scan_angle_rank[self.idx1])
        self.assertEqual(self.p2.scan_angle_rank , 12 , 
            self.scan_angle_rank[self.idx2]) 
 

    def test_raw_classification(self):
        self.assertEqual(self.p1.raw_classification , 1 , 
                self.raw_classification[self.idx1])
        self.assertEqual(self.p2.raw_classification , 2 , 
                 self.raw_classification[self.idx2])


    def test_ptstrcid(self):
        self.assertEqual(self.p1.pt_src_id , 7328 , 
            self.pt_src_id[self.idx1])
        self.assertEqual(self.p2.pt_src_id , 7334 , 
            self.pt_src_id[self.idx2])


    def test_GPSTime(self):
        self.assertTrue(self.p1.gps_time - 2*246504.221932 
                    + self.gps_time[self.idx1] < 0.00001)
        self.assertTrue(self.p2.gps_time - 2*249774.658254 
                    + self.gps_time[self.idx2] < 0.00001)


    def test_red(self):
        self.assertEqual(self.p1.red , 92 , self.red[self.idx1])
        self.assertEqual(self.p2.red , 94 , self.red[self.idx2])


    def test_green(self):
        self.assertEqual(self.p1.green , 100 , self.green[self.idx1])
        self.assertEqual(self.p2.green , 84 , self.green[self.idx2])


    def test_blue(self):
        self.assertEqual(self.p1.blue , 110 , self.blue[self.idx1])
        self.assertEqual(self.p2.blue , 94 , self.blue[self.idx2])
        
    def test_iterator_and_slicing(self):     
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
    def setUp(self):
        inFile = open("../simple.las", "r")
        inData = inFile.read()
        outFile = open("./.temp.las", "w")
        outFile.write(inData)
        outFile.close()
        inFile.close()
        self.FileObject = File.File("./.temp.las", mode = "w")
    
    def test_x(self):
        x = self.FileObject.X + 1
        self.FileObject.X = x
        x2 = self.FileObject.get_x()         
        self.assertTrue(all(x == x2))        
    def test_y(self):
        y = self.FileObject.Y + 1
        self.FileObject.Y = y
        y2 = self.FileObject.get_y()        
        self.assertTrue(all(y == y2))
    def test_z(self):
        z = self.FileObject.Z + 1
        self.FileObject.Z = z
        z2 = self.FileObject.get_z()
        self.assertTrue(all(z == z2))
    def test_intensity(self):
        i = self.FileObject.intensity + 1
        self.FileObject.intensity = i
        i2 = self.FileObject.intensity
        self.assertTrue(all(i == i2))
    def test_return_num(self):
        rn = self.FileObject.return_num + 1
        self.FileObject.return_num = rn
        rn2 = self.FileObject.get_return_num()
        self.assertTrue(all(rn == rn2))
    def test_overflow_return_num(self):
        rn = self.FileObject.return_num + 100000
        with self.assertRaises(Exception):
            self.FileObject.return_num = rn
    def test_num_returns(self):
        nr = self.FileObject.num_returns + 1
        self.FileObject.num_returns = nr
        nr2 = self.FileObject.get_num_returns()
        self.assertTrue(all(nr == nr2))
    def test_scan_dir_flag(self):
        def f(x):
            if x == 1:
                return(0)
            return(1)
        vf = np.vectorize(f) 
        sdf = vf(self.FileObject.scan_dir_flag)
        self.FileObject.scan_dir_flag = sdf
        sdf2 = self.FileObject.get_scan_dir_flag()
        self.assertTrue(all(sdf == sdf2))
    def test_edge_flight_line(self):
        def f(x):
            if x == 1:
                return(0)
            return(1)
        vf = np.vectorize(f)
        efl = vf(self.FileObject.edge_flight_line)
        self.FileObject.edge_flight_line = efl
        efl2 = self.FileObject.get_edge_flight_line()
        self.assertTrue(all(efl == efl2))
    


    def tearDown(self):
        self.FileObject.close()
        os.remove("./.temp.las")


if __name__=="__main__":
    unittest.main()
