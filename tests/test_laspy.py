import os
import time
import unittest
from uuid import UUID

import numpy as np
import pytest

import laspy


def flip_bit(x):
    return 1 * (x == 0)


class LasReaderTestCase(unittest.TestCase):
    simple = os.path.join(os.path.dirname(__file__), "data", "simple.las")
    tempfile = "junk.las"

    def setUp(self):
        self.FileObject = laspy.read(self.simple)
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
        self.withheld = list(LasFile.withheld)
        self.scan_angle_rank = list(LasFile.scan_angle_rank)
        self.user_data = list(LasFile.user_data)
        self.pt_src_id = list(LasFile.pt_src_id)
        ## The following conditional code is redundant for
        ## simple.las, which of course has only one pt. format.
        ## Perhaps find several other files?
        if LasFile.header.point_format.id in (1, 2, 3, 4, 5):
            self.gps_time = list(LasFile.gps_time)
        if LasFile.header.point_format.id in (2, 3, 5):
            self.red = list(LasFile.red)
            self.green = list(LasFile.green)
            self.blue = list(LasFile.blue)
        if LasFile.header.point_format.id in (4, 5):
            self.wave_form_packet_Desc_index = list(LasFile.wave_packet_desc_index)
            self.byte_offset_to_waveform = list(LasFile.byte_offset_to_waveform)
            self.waveform_packet_size = list(LasFile.waveform_packet_size)
            self.return_point_waveform_loc = list(LasFile.return_point_waveform_loc)
            self.x_t = list(LasFile.x_t)
            self.y_t = list(LasFile.y_t)
            self.z_t = list(LasFile.z_t)

        self.p1 = LasFile.points[100]
        self.p2 = LasFile.points[976]

        self.idx1 = 100
        self.idx2 = 976

    def test_x(self):
        """Fetch and test X dimension"""
        self.assertEqual(self.p1.X, 63666106, self.X[self.idx1])
        self.assertEqual(self.p2.X, 63714022, self.X[self.idx2])

    def test_y(self):
        """Fetch and test Y dimension"""
        self.assertEqual(self.p1.Y, 84985413, self.Y[self.idx1])
        self.assertEqual(self.p2.Y, 85318232, self.Y[self.idx2])

    def test_z(self):
        """Fetch and test Z dimension"""
        self.assertEqual(self.p1.Z, 42490, self.Z[self.idx1])
        self.assertEqual(self.p2.Z, 42306, self.Z[self.idx2])

    def test_intensity(self):
        """Fetch and test intensity dimension"""
        self.assertEqual(self.p1.intensity, 233, self.intensity[self.idx1])
        self.assertEqual(self.p2.intensity, 1, self.intensity[self.idx2])

    def test_bit_flags(self):
        """Fetch and test the binary flags associated with flag_byte dimension"""
        self.assertEqual(self.p1.flag_byte, self.flag_byte[self.idx1])
        self.assertEqual(self.p2.flag_byte, self.flag_byte[self.idx2])
        self.assertEqual(self.p1.return_num, self.return_num[self.idx1], 1)
        self.assertEqual(self.p2.return_num, self.return_num[self.idx2], 2)
        self.assertEqual(self.p1.num_returns, self.num_returns[self.idx1], 1)
        self.assertEqual(self.p2.num_returns, self.num_returns[self.idx2], 2)
        self.assertEqual(self.p1.scan_dir_flag, self.scan_dir_flag[self.idx1], 0)
        self.assertEqual(self.p2.scan_dir_flag, self.scan_dir_flag[self.idx2], 1)
        self.assertEqual(self.p1.edge_flight_line, self.edge_flight_line[self.idx1], 0)
        self.assertEqual(self.p2.edge_flight_line, self.edge_flight_line[self.idx2], 0)

    def test_scan_angle_rank(self):
        """Fetch and test scan_angle_rank dimension"""
        self.assertEqual(self.p1.scan_angle_rank, 2, self.scan_angle_rank[self.idx1])
        self.assertEqual(self.p2.scan_angle_rank, 12, self.scan_angle_rank[self.idx2])

    def test_raw_classification(self):
        """Fetch and test the dimension of raw_classification bytes"""
        self.assertEqual(
            self.p1.raw_classification, 1, self.raw_classification[self.idx1]
        )
        self.assertEqual(
            self.p2.raw_classification, 2, self.raw_classification[self.idx2]
        )

    def test_ptstrcid(self):
        """Fetch and test pt_src_id dimension"""
        self.assertEqual(self.p1.pt_src_id, 7328, self.pt_src_id[self.idx1])
        self.assertEqual(self.p2.pt_src_id, 7334, self.pt_src_id[self.idx2])

    def test_GPSTime(self):
        """Fetch and test gps_time dimension"""
        self.assertTrue(
            self.p1.gps_time - 2 * 246504.221932 + self.gps_time[self.idx1] < 0.00001
        )
        self.assertTrue(
            self.p2.gps_time - 2 * 249774.658254 + self.gps_time[self.idx2] < 0.00001
        )

    def test_red(self):
        """Fetch and test red dimension"""
        self.assertEqual(self.p1.red, 92, self.red[self.idx1])
        self.assertEqual(self.p2.red, 94, self.red[self.idx2])

    def test_green(self):
        """Fetch and test green dimension"""
        self.assertEqual(self.p1.green, 100, self.green[self.idx1])
        self.assertEqual(self.p2.green, 84, self.green[self.idx2])

    def test_blue(self):
        """Fetch and test blue dimension"""
        self.assertEqual(self.p1.blue, 110, self.blue[self.idx1])
        self.assertEqual(self.p2.blue, 94, self.blue[self.idx2])


class LasWriterTestCase(unittest.TestCase):
    simple = os.path.join(os.path.dirname(__file__), "data", "simple.las")
    tempfile = "writer.las"
    output_tempfile = "writer_output.las"

    def setUp(self):
        self.FileObject = laspy.read(self.simple)

    def test_x(self):
        """Writing and testing X dimenson"""
        X = self.FileObject.X + 1
        self.FileObject.X = X
        X2 = self.FileObject.X
        self.assertTrue(np.all(X == X2))

        scaled_x = self.FileObject.x
        self.FileObject.x = scaled_x
        self.assertTrue(np.all(scaled_x == self.FileObject.x))

    def test_y(self):
        """Writing and testing Y dimension"""
        Y = self.FileObject.Y + 1
        self.FileObject.Y = Y
        Y2 = self.FileObject.Y
        self.assertTrue(np.all(Y == Y2))

        scaled_y = self.FileObject.y
        self.FileObject.y = scaled_y
        self.assertTrue(np.all(scaled_y == self.FileObject.y))

    def test_z(self):
        """Writing and testing Z dimension"""
        Z = self.FileObject.Z + 1
        self.FileObject.Z = Z
        Z2 = self.FileObject.Z
        self.assertTrue(np.all(Z == Z2))

        scaled_z = self.FileObject.z
        self.FileObject.z = scaled_z
        self.assertTrue(np.all(scaled_z == self.FileObject.z))

    def test_intensity(self):
        """Writing and testing intensity dimension"""
        i = self.FileObject.intensity + 1
        self.FileObject.intensity = i
        i2 = self.FileObject.intensity
        self.assertTrue(np.all(i == i2))

    def test_return_num(self):
        """Writing and testing return_num dimension"""
        rn = self.FileObject.return_num + 1
        self.FileObject.return_num = rn
        rn2 = self.FileObject.return_num
        self.assertTrue(np.all(rn == rn2))

    def test_overflow_return_num(self):
        """Testing overflow handling"""
        rn = self.FileObject.return_num + 100000
        with self.assertRaises(OverflowError):
            self.FileObject.return_num = rn

    def test_num_returns(self):
        """Writing and testing num_returns dimension"""
        nr = self.FileObject.num_returns + 1
        self.FileObject.num_returns = nr
        nr2 = self.FileObject.num_returns
        self.assertTrue(np.all(nr == nr2))

    def test_scan_dir_flag(self):
        """Writing and testing scan_dir_flag dimension"""
        sdf = np.array([flip_bit(x) for x in self.FileObject.scan_dir_flag])
        self.FileObject.scan_dir_flag = sdf
        sdf2 = self.FileObject.scan_dir_flag
        self.assertTrue(np.all(sdf == sdf2))

    def test_edge_flight_line(self):
        """Writing and testing edge_flight_line dimension"""
        efl = np.array([flip_bit(x) for x in self.FileObject.edge_flight_line])
        self.FileObject.edge_flight_line = efl
        efl2 = self.FileObject.edge_flight_line
        self.assertTrue(np.all(efl == efl2))

    def test_classification(self):
        """Writing and testing classification byte."""
        c1 = self.FileObject.classification + 1
        self.FileObject.classification = c1
        c2 = self.FileObject.classification
        self.assertTrue(np.all(c1 == c2))

    def test_synthetic(self):
        """Writing and testing synthetic"""
        s1 = flip_bit(self.FileObject.synthetic)
        self.FileObject.synthetic = s1
        s2 = self.FileObject.synthetic
        self.assertTrue(np.all(s1 == s2))

    def test_key_point(self):
        """Writing and testing key point"""
        k1 = flip_bit(self.FileObject.key_point)
        self.FileObject.key_point = k1
        k2 = self.FileObject.key_point
        self.assertTrue(np.all(k1 == k2))

    def test_withheld(self):
        """Writing and testing withheld"""
        w1 = flip_bit(self.FileObject.withheld)
        self.FileObject.withheld = w1
        w2 = self.FileObject.withheld
        self.assertTrue(np.all(w1 == w2))

    def test_scan_angle_rank(self):
        """Writing and testing scan angle rank"""
        ar1 = self.FileObject.scan_angle_rank
        ar1[ar1 >= 1] -= 1
        self.FileObject.scan_angle_rank = ar1
        ar2 = self.FileObject.scan_angle_rank
        self.assertTrue(np.all(ar1 == ar2))

    def test_user_data(self):
        """Writing and testing user data"""
        ud1 = self.FileObject.user_data + 1
        self.FileObject.user_data = ud1
        ud2 = self.FileObject.user_data
        self.assertTrue(np.all(ud1 == ud2))

    def test_pt_src_id(self):
        """Writing and testing point source id"""
        p1 = self.FileObject.user_data + 1
        self.FileObject.user_data = p1
        p2 = self.FileObject.user_data
        self.assertTrue(np.all(p1 == p2))

    def test_gps_time(self):
        """Writing and testing gps time"""
        g1 = self.FileObject.gps_time + 1.0
        self.FileObject.gps_time = g1
        g2 = self.FileObject.gps_time
        self.assertTrue(np.all(g1 == g2))

    def test_red(self):
        """Writing and testing red"""
        r1 = self.FileObject.red + 1
        self.FileObject.red = r1
        r2 = self.FileObject.red
        self.assertTrue(np.all(r1 == r2))

    def test_green(self):
        """Writing and testing green"""
        g1 = self.FileObject.green + 1
        self.FileObject.green = g1
        g2 = self.FileObject.green
        self.assertTrue(np.all(g1 == g2))

    def test_blue(self):
        """Writing and testing blue"""
        b1 = self.FileObject.blue + 1
        self.FileObject.blue = b1
        b2 = self.FileObject.blue
        self.assertTrue(np.all(b1 == b2))

    # def test_vlr_defined_dimensions2(self):
    #     """Testing VLR defined dimension API"""
    #     File2 = File.File(self.output_tempfile, mode="w", header=self.FileObject.header)
    #     File2.define_new_dimension("test_dimension", 5, "This is a test.")
    #     File2.X = self.FileObject.X
    #     self.assertTrue(File2.test_dimension[500] == 0)
    #     File2.close(ignore_header_changes=True)

    def tearDown(self):
        self.FileObject.write(self.output_tempfile)
        really_remove(self.output_tempfile)


class LasHeaderWriterTestCase(unittest.TestCase):
    simple = os.path.join(os.path.dirname(__file__), "data", "simple.las")
    simple14 = os.path.join(os.path.dirname(__file__), "data", "simple1_4.las")
    tempfile = os.path.abspath("headerwriter.las")
    tempfile2 = os.path.abspath("headerwriter2.las")

    def setUp(self):
        self.las = laspy.read(self.simple)

    def test_file_src(self):
        """Testing file_src"""
        f1 = self.las.header.file_source_id + 1
        self.las.header.file_source_id = f1
        f2 = self.las.header.file_source_id
        assert f1 == f2

    @pytest.mark.skip(reason="API changed")
    def test_uuid(self):
        """Testing uuid"""
        guid = self.las.header.guid
        guid2 = self.las.header.project_id
        self.assertEqual(guid, guid2)
        newGuid = UUID(bytes=b"1" * 16)
        self.las.header.guid = newGuid
        newGuid2 = self.las.header.get_guid()
        self.assertEqual(newGuid, newGuid2)

    def test_versions(self):
        """Testing Versions"""
        assert self.las.header.version.major == 1
        with self.assertRaises(AttributeError):
            self.las.header.version.major = 2

    def test_system_id(self):
        """Testing System ID"""
        sys1 = self.las.header.system_identifier
        sys1 = "1234567891" + sys1[10:]
        self.las.header.system_identifier = sys1
        sys2 = self.las.header.system_identifier
        assert sys1 == sys2

    def test_software_id(self):
        """"Testing Software ID"""
        s1 = self.las.header.generating_software
        s1 = "1234567" + s1[7:]
        self.las.header.generating_software = s1
        s2 = self.las.header.generating_software
        assert s1 == s2
        # with self.assertRaises(laspy.LaspyException):
        #     self.las.header.generating_software = "123"
        # with self.assertRaises(laspy.LaspyException):
        #     self.las.header.generating_software = "1" * 100

    def test_date(self):
        """Testing Date"""
        d1 = self.las.header.creation_date
        assert d1 is None
        from datetime import datetime

        d2 = datetime(2007, 12, 10)
        self.las.header.creation_date = d2
        d3 = self.las.header.creation_date
        self.assertEqual(d2, d3)

    def test_point_recs_by_return(self):
        """Testing point records by return"""
        r1 = self.las.header.number_of_points_by_return + 1
        self.las.header.number_of_points_by_return = r1
        r2 = self.las.header.number_of_points_by_return
        assert np.all(r1 == r2)

    def test_min_max_update(self):
        """Testing the update min/max function"""
        x = self.las.X
        x[0] = max(x) + 1
        y = self.las.Y
        y[0] = max(y) + 1
        z = self.las.Z
        z[0] = max(z) + 1
        self.las.X = x
        self.las.Y = y
        self.las.Z = z
        self.las.update_header()
        file_max = self.las.header.maxs
        assert np.all(file_max == [self.las.x[0], self.las.y[0], self.las.z[0]])

    def test_histogram(self):
        """Testing the update_histogram functon"""
        h1 = self.las.header.number_of_points_by_return
        self.las.update_header()
        h2 = self.las.header.number_of_points_by_return
        assert np.all(h1 == h2)

    def test_offset(self):
        """Testing offset"""
        o1 = self.las.header.offsets
        o1[0] += 1
        self.las.header.offsets = o1
        o2 = self.las.header.offsets
        assert np.all(o1 == o2)

    def test_scale(self):
        """Testing Scale"""
        s1 = self.las.header.scales
        s1[0] += 1
        self.las.header.scales = s1
        s2 = self.las.header.scales
        assert np.all(s1 == s2)


class LasWriteModeTestCase(unittest.TestCase):
    simple = os.path.join(os.path.dirname(__file__), "data", "simple.las")
    tempfile = "write-mode.las"
    output_tempfile = "write-mode-output.las"

    def setUp(self):
        self.File1 = laspy.read(self.simple)

    def test_using_barebones_header(self):
        """Testing file creation using barebones header"""
        header = laspy.LasHeader()

        File2 = laspy.LasData(header)

        self.assertTrue(File2.header.version == "1.2")

        X = self.File1.X
        Y = self.File1.Y
        Z = self.File1.Z
        File2.X = X
        File2.Y = Y
        File2.Z = Z

        File2.write(self.output_tempfile)
        File2 = laspy.read(self.output_tempfile)

        self.assertTrue(np.all(X == File2.X))
        self.assertTrue(np.all(Y == File2.Y))
        self.assertTrue(np.all(Z == File2.Z))

    def test_using_existing_header(self):
        """Test file creation using an existing header"""
        File2 = laspy.LasData(self.File1.header)
        X = self.File1.X
        Y = self.File1.Y
        Z = self.File1.Z
        File2.X = X
        File2.Y = Y
        File2.Z = Z

        File2.write(self.output_tempfile)
        File2 = laspy.read(self.output_tempfile)

        self.assertTrue(np.all(X == File2.X))
        self.assertTrue(np.all(Y == File2.Y))
        self.assertTrue(np.all(Z == File2.Z))

    def tearDown(self):
        really_remove(self.output_tempfile)


class LasV_13TestCase(unittest.TestCase):
    simple = os.path.join(os.path.dirname(__file__), "data", "simple1_3.las")
    output_tempfile = "v13-output.las"

    def setUp(self):
        self.File1 = laspy.read(self.simple)

    def test_glob_encode(self):
        """Testing v1.3 Global Encoding"""
        old = self.File1.header.global_encoding.gps_time_type
        assert old == laspy.header.GpsTimeType.WEEK_TIME
        self.File1.header.global_encoding.gps_time_type = (
            laspy.header.GpsTimeType.STANDARD
        )
        assert (
            self.File1.header.global_encoding.gps_time_type
            == laspy.header.GpsTimeType.STANDARD
        )

        self.File1.header.global_encoding.gps_time_type = (
            laspy.header.GpsTimeType.WEEK_TIME
        )
        assert (
            self.File1.header.global_encoding.gps_time_type
            == laspy.header.GpsTimeType.WEEK_TIME
        )

        File2 = laspy.LasData(self.File1.header)
        File2.write(self.output_tempfile)
        File2 = laspy.read(self.output_tempfile)

        self.assertEqual(
            self.File1.header.global_encoding.waveform_data_packets_internal,
            File2.header.global_encoding.waveform_data_packets_internal,
        )
        self.assertEqual(
            self.File1.header.global_encoding.waveform_data_packets_external,
            File2.header.global_encoding.waveform_data_packets_external,
        )
        self.assertEqual(
            self.File1.header.global_encoding.synthetic_return_numbers,
            File2.header.global_encoding.synthetic_return_numbers,
        )

    def test_wave_packet_desc_index(self):
        """Testing wave_packet_desc_index."""
        test1 = self.File1.wave_packet_desc_index
        File2 = laspy.LasData(self.File1.header)
        File2.points = self.File1.points
        assert np.all(test1 == File2.wave_packet_desc_index)

    def test_byte_offset_to_waveform_data(self):
        """Testing byte_offset_to_waveform_data"""
        test1 = self.File1.byte_offset_to_waveform_data
        File2 = laspy.LasData(self.File1.header)
        File2.points = self.File1.points
        assert np.all(test1 == File2.byte_offset_to_waveform_data)

    def test_waveform_packet_size(self):
        """Testing waveform_packet_size"""
        test1 = self.File1.waveform_packet_size
        File2 = laspy.LasData(self.File1.header)
        File2.points = self.File1.points.copy()
        assert np.all(test1 == File2.waveform_packet_size)

    def test_return_point_waveform_loc(self):
        """Testing return_point_waveform_loc"""
        test1 = self.File1.return_point_waveform_loc
        File2 = laspy.LasData(self.File1.header)
        File2.points = self.File1.points.copy()
        assert np.all(test1 == File2.return_point_waveform_loc)
        File2.return_point_waveform_loc += 1
        assert np.all(test1 != File2.return_point_waveform_loc)

    def test_x_t(self):
        """Testing x_t"""
        test1 = self.File1.x_t
        File2 = laspy.LasData(self.File1.header)
        File2.points = self.File1.points.copy()
        assert np.all(test1 == File2.x_t)
        File2.x_t += 1
        assert np.all(test1 != File2.x_t)

    def test_y_t(self):
        """Testing y_t"""
        test1 = self.File1.y_t
        File2 = laspy.LasData(self.File1.header)
        File2.points = self.File1.points.copy()
        np.all(test1 == File2.y_t)
        File2.y_t += 1
        assert np.all(test1 != File2.y_t)

    def test_z_t(self):
        """Testing z_t"""
        test1 = self.File1.z_t
        File2 = laspy.LasData(self.File1.header)
        File2.points = self.File1.points.copy()
        np.all(test1 == File2.z_t)
        File2.z_t += 1
        np.all(test1 != File2.z_t)

    def tearDown(self):
        really_remove(self.output_tempfile)


class LasV_14TestCase(unittest.TestCase):
    simple = os.path.join(os.path.dirname(__file__), "data", "simple1_4.las")
    tempfile = "v14.las"
    output_tempfile = "v14-output.las"

    def setUp(self):
        self.File1 = laspy.read(self.simple)

    def test_glob_encode(self):
        """Testing v1.4 Global Encoding"""
        old = self.File1.header.global_encoding.gps_time_type
        assert old == laspy.header.GpsTimeType.WEEK_TIME
        self.File1.header.global_encoding.gps_time_type = (
            laspy.header.GpsTimeType.STANDARD
        )
        assert (
            self.File1.header.global_encoding.gps_time_type
            == laspy.header.GpsTimeType.STANDARD
        )

        File2 = laspy.LasData(self.File1.header)
        self.assertEqual(
            self.File1.header.global_encoding.waveform_data_packets_internal,
            File2.header.global_encoding.waveform_data_packets_internal,
        )
        self.assertEqual(
            self.File1.header.global_encoding.waveform_data_packets_external,
            File2.header.global_encoding.waveform_data_packets_external,
        )
        self.assertEqual(
            self.File1.header.global_encoding.synthetic_return_numbers,
            File2.header.global_encoding.synthetic_return_numbers,
        )

    def test_glob_encode_bits(self):
        b1 = self.File1.header.global_encoding.gps_time_type
        b2 = self.File1.header.global_encoding.waveform_data_packets_internal
        b3 = self.File1.header.global_encoding.waveform_data_packets_external
        b4 = self.File1.header.global_encoding.synthetic_return_numbers
        b5 = self.File1.header.global_encoding.wkt

        bf1 = 1 - int(b1)
        bf2 = 1 - int(b2)
        bf3 = 1 - int(b3)
        bf4 = 1 - int(b4)
        bf5 = 1 - int(b5)

        self.File1.header.global_encoding.gps_time_type = bf1
        self.File1.header.global_encoding.waveform_data_packets_internal = bf2
        self.File1.header.global_encoding.waveform_data_packets_external = bf3
        self.File1.header.global_encoding.synthetic_return_numbers = bf4
        self.File1.header.global_encoding.wkt = bf5

        assert self.File1.header.global_encoding.gps_time_type == bf1
        assert self.File1.header.global_encoding.waveform_data_packets_internal == bf2
        assert self.File1.header.global_encoding.waveform_data_packets_external == bf3
        assert self.File1.header.global_encoding.synthetic_return_numbers == bf4
        assert self.File1.header.global_encoding.wkt == bf5

    def test_classification_variables(self):
        """Testing v1.4 classification support"""
        classification = self.File1.classification
        classification_flags = self.File1.classification_flags
        scanner_channel = self.File1.scanner_channel
        scan_dir_flag = self.File1.scan_dir_flag
        edge_flight_line = self.File1.edge_flight_line

        return_num = self.File1.return_num
        num_returns = self.File1.num_returns

        File2 = laspy.LasData(self.File1.header)
        File2.classification = classification
        File2.classification_flags = classification_flags
        File2.scan_dir_flag = scan_dir_flag
        File2.scanner_channel = scanner_channel
        File2.edge_flight_line = edge_flight_line
        File2.return_num = return_num
        File2.num_returns = num_returns

        File2.write(self.output_tempfile)
        File2 = laspy.read(self.output_tempfile)

        assert np.all(num_returns == File2.num_returns)
        assert np.all(return_num == File2.return_num)
        assert np.all(edge_flight_line == File2.edge_flight_line)
        assert np.all(scan_dir_flag == File2.scan_dir_flag)
        assert np.all(classification_flags == File2.classification_flags)
        assert np.all(classification == File2.classification)
        assert np.all(scanner_channel == File2.scanner_channel)

    def tearDown(self):
        really_remove(self.output_tempfile)


def really_remove(path, max_=1):
    """
    Hack for Windows when quickly creating and deleting files.
    os.remove can return when Windows still thinks the file exists.
    When trying to re-create the file with the same name, a PermissionError occurs.
    :param path: path to remove
    :param max_: max seconds to wait
    """
    wait = 0.01
    while os.path.exists(path):
        try:
            os.remove(path)
        except WindowsError:
            time.sleep(wait)
            max_ -= wait
            if max_ <= 0:
                break
