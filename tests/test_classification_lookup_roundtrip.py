import io
import struct

import pytest

import laspy
from laspy.vlrs.known import ClassificationLookupVlr


def packed(entries):
    return b"".join(struct.pack("<B15s", number, text) for number, text in entries)


RECORDS = [
    (7, b"first_name"),
    (2, b"middle-point"),
    (7, b"last.name"),
    (0, b"zero,+ /"),
    (255, b"123456789012345"),
    (2, b"final_value"),
]
VISIBLE = [
    (7, "last.name"),
    (2, "final_value"),
    (0, "zero,+ /"),
    (255, "123456789012345"),
]


@pytest.mark.parametrize(
    "description",
    [
        b"under_score",
        b"hyphen-name",
        b"dot.name",
        b"comma, space",
        b"[]()/+!?:;='\"",
        b"123456789012345",
        b"trail spaces  ",
    ],
)
def test_lookup_preserves_ascii_description_and_exact_bytes(description):
    raw = packed([(255, description)])
    lookup = ClassificationLookupVlr()
    lookup.parse_record_data(raw)
    assert lookup[255] == description.decode("ascii")
    assert lookup.record_data_bytes() == raw


def test_lookup_stops_at_first_nul_and_preserves_unused_bytes():
    raw = packed([(0, b"name\0old-tail\xff")])
    lookup = ClassificationLookupVlr()
    lookup.parse_record_data(raw)
    assert lookup[0] == "name"
    assert lookup.record_data_bytes() == raw


def test_duplicate_lookup_records_preserve_order_and_last_value_mapping():
    raw = packed(RECORDS)
    lookup = ClassificationLookupVlr()
    lookup.parse_record_data(raw)
    assert isinstance(lookup.lookups, dict)
    assert list(lookup.lookups.items()) == VISIBLE
    assert lookup[7] == "last.name"
    assert lookup[2] == "final_value"
    assert lookup.record_data_bytes() == raw
    assert lookup.record_data_bytes() == raw
    assert list(lookup.lookups.items()) == VISIBLE


@pytest.mark.parametrize(
    "operation", ["item", "direct", "update", "delete", "clear", "reorder", "replace"]
)
def test_edited_lookup_uses_existing_ordered_dictionary_serialization(operation):
    lookup = ClassificationLookupVlr()
    lookup.parse_record_data(packed(RECORDS))
    if operation == "item":
        lookup[7] = "edited-name"
        expected = [(7, "edited-name"), *VISIBLE[1:]]
    elif operation == "direct":
        lookup.lookups[2] = "direct.name"
        expected = [VISIBLE[0], (2, "direct.name"), *VISIBLE[2:]]
    elif operation == "update":
        lookup.lookups.update({7: "updated", 9: "added-role"})
        expected = [(7, "updated"), *VISIBLE[1:], (9, "added-role")]
    elif operation == "delete":
        del lookup.lookups[7]
        expected = VISIBLE[1:]
    elif operation == "clear":
        lookup.lookups.clear()
        expected = []
    elif operation == "reorder":
        value = lookup.lookups.pop(7)
        lookup.lookups[7] = value
        expected = [*VISIBLE[1:], VISIBLE[0]]
    else:
        lookup.lookups = {255: "replacement"}
        expected = [(255, "replacement")]
    assert list(lookup.lookups.items()) == expected
    canonical = packed([(number, name.encode("ascii")) for number, name in expected])
    assert lookup.record_data_bytes() == canonical
    reparsed = ClassificationLookupVlr()
    reparsed.parse_record_data(canonical)
    assert list(reparsed.lookups.items()) == expected


def test_restoring_original_mapping_restores_original_records():
    raw = packed(RECORDS)
    lookup = ClassificationLookupVlr()
    lookup.parse_record_data(raw)
    lookup[7] = "temporary"
    lookup[7] = "last.name"
    assert lookup.record_data_bytes() == raw
    lookup.lookups = dict(VISIBLE)
    assert lookup.record_data_bytes() == raw


def test_parse_reuse_replaces_contents_but_keeps_public_dictionary():
    lookup = ClassificationLookupVlr()
    public_mapping = lookup.lookups
    lookup.parse_record_data(packed(RECORDS))
    replacement = packed([(3, b"new.record")])
    lookup.parse_record_data(replacement)
    assert lookup.lookups is public_mapping
    assert lookup.lookups == {3: "new.record"}
    assert lookup.record_data_bytes() == replacement
    lookup.parse_record_data(b"")
    assert lookup.lookups is public_mapping
    assert lookup.lookups == {}
    assert lookup.record_data_bytes() == b""


@pytest.mark.parametrize("size", [1, 15, 17, 31])
def test_truncated_lookup_rejects_without_changing_previous_record(size):
    lookup = ClassificationLookupVlr()
    original = packed(RECORDS)
    lookup.parse_record_data(original)
    with pytest.raises(struct.error):
        lookup.parse_record_data(b"x" * size)
    assert list(lookup.lookups.items()) == VISIBLE
    assert lookup.record_data_bytes() == original


def test_non_ascii_description_rejects_without_partial_mapping_update():
    lookup = ClassificationLookupVlr()
    original = packed(RECORDS)
    lookup.parse_record_data(original)
    with pytest.raises(UnicodeDecodeError):
        lookup.parse_record_data(packed([(1, b"valid"), (2, b"bad\x80name")]))
    assert list(lookup.lookups.items()) == VISIBLE
    assert lookup.record_data_bytes() == original


def test_mutable_input_does_not_mutate_saved_record():
    raw = packed(RECORDS)
    source = bytearray(raw)
    lookup = ClassificationLookupVlr()
    lookup.parse_record_data(source)
    source[:] = b"x" * len(source)
    assert lookup.record_data_bytes() == raw


@pytest.mark.parametrize(
    "name", ["x" * 16, "non-ascii\N{LATIN SMALL LETTER E WITH ACUTE}"]
)
def test_edited_descriptions_retain_serialization_validation(name):
    lookup = ClassificationLookupVlr()
    lookup.parse_record_data(packed(RECORDS))
    lookup[7] = name
    with pytest.raises(ValueError):
        lookup.record_data_bytes()


@pytest.mark.parametrize("number", [-1, 256])
def test_public_setter_retains_id_validation(number):
    lookup = ClassificationLookupVlr()
    with pytest.raises(ValueError):
        lookup[number] = "name"


@pytest.mark.parametrize("backend", [None, *laspy.LazBackend.detect_available()])
def test_las_roundtrip_preserves_lookup_payload(backend):
    original = packed(RECORDS)
    lookup = ClassificationLookupVlr()
    lookup.parse_record_data(original)
    header = laspy.LasHeader(point_format=6, version="1.4")
    header.vlrs.append(lookup)
    data = laspy.LasData(header)
    data.points = laspy.ScaleAwarePointRecord.zeros(2, header=header)
    first = io.BytesIO()
    data.write(first, do_compress=backend is not None, laz_backend=backend)
    result = laspy.read(io.BytesIO(first.getvalue()))
    recovered = result.vlrs.get("ClassificationLookupVlr")[0]
    assert list(recovered.lookups.items()) == VISIBLE
    assert recovered.record_data_bytes() == original
    second = io.BytesIO()
    result.write(second, do_compress=backend is not None, laz_backend=backend)
    assert (
        laspy.read(io.BytesIO(second.getvalue()))
        .vlrs.get("ClassificationLookupVlr")[0]
        .record_data_bytes()
        == original
    )
