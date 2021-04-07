import laspy
from laspy import PointFormat


def test_lost_dims():
    assert set(laspy.point.format.lost_dimensions(3, 0)) == {
        "red",
        "green",
        "blue",
        "gps_time",
    }
    assert set(laspy.point.format.lost_dimensions(2, 0)) == {"red", "green", "blue"}
    assert set(laspy.point.format.lost_dimensions(1, 0)) == {"gps_time"}

    assert set(laspy.point.format.lost_dimensions(0, 0)) == set()
    assert set(laspy.point.format.lost_dimensions(0, 1)) == set()
    assert set(laspy.point.format.lost_dimensions(0, 2)) == set()
    assert set(laspy.point.format.lost_dimensions(0, 3)) == set()


def test_has_waveform():
    for i in (4, 5, 9, 10):
        assert PointFormat(
            i
        ).has_waveform_packet, "Point format {} should have waveform".format(i)

    for i in (0, 1, 2, 3, 6, 7, 8):
        assert not PointFormat(
            i
        ).has_waveform_packet, "Point format {} should not have waveform".format(i)


def test_extra_bytes_struct_size():
    assert laspy.vlrs.known.ExtraBytesStruct.size() == 192


def test_waveform_packet_struct_size():
    assert laspy.vlrs.known.WaveformPacketStruct.size() == 26
