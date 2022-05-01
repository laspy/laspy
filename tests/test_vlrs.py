from pathlib import Path

import pytest

import laspy
from tests import test_common


def test_adding_classification_lookup():
    simple = laspy.read(test_common.simple_las)
    classification_lookup = laspy.vlrs.known.ClassificationLookupVlr()

    assert len(classification_lookup.lookups) == 0
    classification_lookup[20] = "computer"
    assert len(classification_lookup.lookups) == 1
    classification_lookup[17] = "car"

    simple.vlrs.append(classification_lookup)

    simple = test_common.write_then_read_again(simple)
    classification_lookups = simple.vlrs.get("ClassificationLookupVlr")[0]

    assert classification_lookups[20] == "computer"
    assert classification_lookups[17] == "car"


def test_lookup_out_of_range():
    classification_lookup = laspy.vlrs.known.ClassificationLookupVlr()
    with pytest.raises(ValueError):
        classification_lookup[541] = "LiquidWater"

    with pytest.raises(ValueError):
        classification_lookup[-42] = "SolidWater"


def test_adding_extra_bytes_vlr_by_hand():
    """
    Test that if someone adds an ExtraBytesVlr by himself
    without having matching extra bytes in the point record, the
    ExtraByteVlr is removed before writing
    """

    simple = laspy.read(test_common.simple_las)
    ebvlr = laspy.vlrs.known.ExtraBytesVlr()
    ebs = laspy.vlrs.known.ExtraBytesStruct(data_type=3, name="Fake".encode())
    ebvlr.extra_bytes_structs.append(ebs)
    simple.vlrs.append(ebvlr)
    assert len(simple.vlrs.get("ExtraBytesVlr")) == 1

    las = laspy.lib.write_then_read_again(simple)
    assert simple.points.point_size == las.points.point_size
    assert len(las.vlrs.get("ExtraBytesVlr")) == 0

