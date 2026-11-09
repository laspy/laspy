import io

import numpy as np
import pytest

import laspy
from laspy.errors import LaspyException
from laspy.vlrs.known import WktCoordinateSystemVlr
from laspy.vlrs.vlrlist import VLRList

WKT = (
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,'
    '298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
)
BACKENDS = [None, *laspy.LazBackend.detect_available()]


def extended_bytes(records):
    stream = io.BytesIO()
    records.write_to(stream, as_extended=True)
    return stream.getvalue()


def synthetic_source(count=3):
    header = laspy.LasHeader(point_format=6, version="1.4")
    header.global_encoding.wkt = True
    header.vlrs.append(laspy.VLR("ordinary", 11, "ordinary VLR", b"ordinary"))
    header.evlrs = VLRList(
        [
            WktCoordinateSystemVlr(WKT),
            laspy.VLR("synthetic", 42, "opaque extended", b"opaque\0\xffpayload"),
        ]
    )
    data = laspy.LasData(header)
    data.points = laspy.ScaleAwarePointRecord.zeros(count, header=header)
    data.x = np.arange(count)
    data.y = np.arange(count) * 2
    data.z = np.arange(count) * -3
    stream = io.BytesIO()
    data.write(stream, do_compress=False)
    return stream.getvalue()


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("count", [0, 3])
def test_streaming_preserves_inherited_evlrs(backend, count):
    source = synthetic_source(count)
    destination = io.BytesIO()
    with laspy.open(io.BytesIO(source)) as reader:
        original = (
            reader.header.number_of_evlrs,
            reader.header.start_of_first_evlr,
            reader.header.global_encoding.value,
            extended_bytes(reader.header.evlrs),
        )
        with laspy.open(
            destination,
            mode="w",
            header=reader.header,
            do_compress=backend is not None,
            laz_backend=backend,
            closefd=False,
        ) as writer:
            for points in reader.chunk_iterator(2):
                writer.write_points(points)
        assert (
            reader.header.number_of_evlrs,
            reader.header.start_of_first_evlr,
            reader.header.global_encoding.value,
            extended_bytes(reader.header.evlrs),
        ) == original
    result = laspy.read(io.BytesIO(destination.getvalue()))
    assert result.header.number_of_evlrs == 2
    assert result.header.global_encoding.wkt
    assert result.header.global_encoding.value == original[2]
    assert extended_bytes(result.evlrs) == original[3]
    assert destination.getvalue()[result.header.start_of_first_evlr :] == original[3]
    assert result.header.start_of_first_evlr >= result.header.offset_to_point_data
    assert result.header.point_count == count
    assert np.array_equal(result.x, np.arange(count))
    assert np.array_equal(result.y, np.arange(count) * 2)
    assert np.array_equal(result.z, np.arange(count) * -3)
    assert result.header.vlrs[0].record_data_bytes() == b"ordinary"
    assert result.evlrs[0].string == WKT


def test_streamed_wkt_crs_is_parseable():
    pyproj = pytest.importorskip("pyproj")
    destination = io.BytesIO()
    with laspy.open(io.BytesIO(synthetic_source())) as reader:
        with laspy.open(
            destination, mode="w", header=reader.header, closefd=False
        ) as writer:
            for points in reader.chunk_iterator(2):
                writer.write_points(points)
    result = laspy.read(io.BytesIO(destination.getvalue()))
    assert result.header.parse_crs() == pyproj.CRS.from_wkt(WKT)


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("empty", [False, True])
def test_explicit_evlrs_replace_inheritance_once(backend, empty):
    destination = io.BytesIO()
    replacement = VLRList(
        [] if empty else [laspy.VLR("replacement", 77, "replacement", b"new")]
    )
    with laspy.open(io.BytesIO(synthetic_source())) as reader:
        with laspy.open(
            destination,
            mode="w",
            header=reader.header,
            do_compress=backend is not None,
            laz_backend=backend,
            closefd=False,
        ) as writer:
            writer.write_points(reader.read_points(3))
            writer.write_evlrs(replacement)
    result = laspy.read(io.BytesIO(destination.getvalue()))
    assert result.header.number_of_evlrs == len(replacement)
    assert extended_bytes(result.evlrs) == extended_bytes(replacement)
    if empty:
        assert result.header.start_of_first_evlr == 0
    else:
        assert destination.getvalue()[
            result.header.start_of_first_evlr :
        ] == extended_bytes(replacement)


@pytest.mark.parametrize("evlrs", [None, VLRList()])
def test_absent_inherited_evlrs(evlrs):
    header = laspy.LasHeader(point_format=6, version="1.4")
    header.evlrs = evlrs
    destination = io.BytesIO()
    writer = laspy.open(destination, mode="w", header=header, closefd=False)
    writer.close()
    first = destination.getvalue()
    writer.close()
    assert destination.getvalue() == first
    result = laspy.read(io.BytesIO(first))
    assert result.header.number_of_evlrs == 0
    assert result.header.start_of_first_evlr == 0
    assert result.header.point_count == 0


def test_inherited_evlrs_not_duplicated_on_second_close():
    destination = io.BytesIO()
    with laspy.open(io.BytesIO(synthetic_source())) as reader:
        writer = laspy.open(destination, mode="w", header=reader.header, closefd=False)
        writer.write_points(reader.read_points(3))
        writer.close()
        first = destination.getvalue()
        writer.close()
        assert destination.getvalue() == first
    assert laspy.read(io.BytesIO(first)).header.number_of_evlrs == 2


def test_older_las_keeps_existing_evlr_rejection():
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.evlrs = VLRList([laspy.VLR("synthetic", 42, "unsupported", b"old")])
    destination = io.BytesIO()
    with laspy.open(destination, mode="w", header=header, closefd=False) as writer:
        with pytest.raises(LaspyException, match="version less than 1.4"):
            writer.write_evlrs(header.evlrs)
    result = laspy.read(io.BytesIO(destination.getvalue()))
    assert result.header.version == "1.2"
    assert result.header.point_count == 0
    assert not result.evlrs


@pytest.mark.parametrize("version", ["1.4", "1.5"])
@pytest.mark.parametrize("closefd", [False, True])
@pytest.mark.parametrize("close_fails", [False, True])
def test_inherited_evlr_failure_closes_only_owned_stream(version, closefd, close_fails):
    payload = b"synthetic partial EVLR payload"
    write_error = OSError("synthetic EVLR write failure")

    class FailingStream(io.BytesIO):
        close_calls = 0
        snapshot = None

        def write(self, data):
            if bytes(data) == payload:
                super().write(data[:3])
                raise write_error
            return super().write(data)

        def close(self):
            self.close_calls += 1
            self.snapshot = self.getvalue()
            if close_fails:
                raise OSError("synthetic stream close failure")
            super().close()

    header = laspy.LasHeader(point_format=6, version=version)
    header.evlrs = VLRList([laspy.VLR("synthetic", 42, "partial", payload)])
    stream = FailingStream()
    try:
        with pytest.raises(OSError, match="synthetic EVLR write failure") as failure:
            with laspy.open(stream, mode="w", header=header, closefd=closefd) as writer:
                pass
        assert failure.value is write_error
        assert stream.close_calls == int(closefd)
        assert stream.closed is (closefd and not close_fails)
        if closefd and close_fails:
            assert any(
                "synthetic stream close failure" in note
                for note in write_error.__notes__
            )
        contents = stream.snapshot if closefd else stream.getvalue()
        # The failed file must retain its initial uncommitted EVLR header.
        on_disk_header = laspy.LasHeader.read_from(io.BytesIO(contents))
        assert on_disk_header.number_of_evlrs == 0
        assert on_disk_header.start_of_first_evlr == 0
        with pytest.raises(OSError) as repeated:
            writer.close()
        assert repeated.value is write_error
        if not stream.closed:
            assert stream.getvalue() == contents
        assert stream.close_calls == int(closefd)
    finally:
        # Fixture retirement bypasses its deliberately failing close override.
        io.BytesIO.close(stream)


def test_inherited_evlrs_supported_in_las_1_5():
    header = laspy.LasHeader(point_format=6, version="1.5")
    header.evlrs = VLRList([laspy.VLR("synthetic", 42, "inherited", b"LAS1.5")])
    destination = io.BytesIO()
    with laspy.open(destination, mode="w", header=header, closefd=False):
        pass
    result = laspy.read(io.BytesIO(destination.getvalue()))
    assert result.header.version == "1.5"
    assert result.header.number_of_evlrs == 1
    assert result.evlrs[0].record_data_bytes() == b"LAS1.5"
