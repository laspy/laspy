""" The functions related to the LAZ format (compressed LAS)
"""
import enum
from typing import Tuple

import laspy


class LazBackend(enum.Enum):
    """Supported backends for reading and writing LAS/LAZ"""

    # type_hint = Union[LazBackend, Iterable[LazBackend]]

    LazrsParallel = 0
    """lazrs in multi-thread mode"""
    Lazrs = 1
    """lazrs in single-thread mode"""
    Laszip = 2
    """laszip backend"""

    def is_available(self) -> bool:
        """Returns true if the backend is available"""
        if self == LazBackend.Lazrs or self == LazBackend.LazrsParallel:
            try:
                import lazrs
            except ModuleNotFoundError:
                return False
            else:
                return True
        elif self == LazBackend.Laszip:
            try:
                import laszip
            except ModuleNotFoundError:
                return False
            else:
                return True
        else:
            return False

    @staticmethod
    def detect_available() -> Tuple["LazBackend", ...]:
        """Returns a tuple containing the available backends in the current
        python environment
        """
        available_backends = []

        if LazBackend.LazrsParallel.is_available():
            available_backends.append(LazBackend.LazrsParallel)
            available_backends.append(LazBackend.Lazrs)

        if LazBackend.Laszip.is_available():
            available_backends.append(LazBackend.Laszip)

        return tuple(available_backends)


def decompress_and_skip_methods(wrapped_enum):
    """This decorator is to be applied on an enum.IntFlag class

    It will add to this enum some methods:

    - set(self, flag_name) -> Self => to easily set a flag
    - unset(self, flag_name) -> Self => to easily unset a flag
    - is_set(self, flag_name) -> bool => to easily check if a flag is set


    If will also add for each flag member (as long as their name is uppercase)
    the following methods

    - decompress_$flag(self) -> Self
    - skip_$flag(self) -> Self


    # Example

    @load_and_skip_methods
    class Color(IntFlag):
        RED = 1
        GREEN = 2
        BLUE = 4


    will generate (ellipsis to keep it short)

    class Color(IntFlag):
        RED = 1
        GREEN = 2

    def _set(self, mask): ...

    def _unset(self, mask): ...

    def is_set(self, mask): ...


    def decompress_red(self) -> Color: ...
    def decompress_red(self) -> Color : ...
    def is_set_red(self) -> Color : ...
    def load_green(self) -> Color: ...
    def skip_green(self) -> Color: ...
    def is_set_green(self) -> Color : ...
    """

    def set_method(self, mask) -> wrapped_enum:
        return self | mask

    def unset_method(self, mask) -> wrapped_enum:
        return self & (~mask)

    def is_set_method(self, mask) -> bool:
        return (self & mask) != 0

    setattr(wrapped_enum, "_set", set_method)
    setattr(wrapped_enum, "_unset", unset_method)
    setattr(wrapped_enum, "is_set", is_set_method)

    def define_skip_method(mask_member_name: str):
        def skip_method(self):
            return self._unset(getattr(self, mask_member_name))

        return skip_method

    def define_decompress_method(mask_member_name: str):
        def decompress_method(self):
            return self._set(getattr(self, mask_member_name))

        return decompress_method

    def define_is_set_method(mask_member_name: str):
        def is_set_method(self):
            return self.is_set(getattr(self, mask_member_name))

        return is_set_method

    for member in dir(wrapped_enum):
        if not member.isupper():
            continue

        load_name = f"decompress_{member.lower()}"
        skip_name = f"skip_{member.lower()}"
        is_set_name = f"is_set_{member.lower()}"

        setattr(wrapped_enum, load_name, define_decompress_method(member))
        setattr(wrapped_enum, skip_name, define_skip_method(member))
        setattr(wrapped_enum, is_set_name, define_is_set_method(member))

    return wrapped_enum


@decompress_and_skip_methods
class DecompressionSelection(enum.IntFlag):
    """
    Holds which fields to decompress  or not.

    Only used for files with version >= 1.4 && point format id >= 6.

    Ignored on other cases.


    Each flag in the enum has a corresponding ``decompress_$name`` and
    ``skip_$name`` methods to easily create a selection.

    >>> import laspy
    >>> # Creating a selection that decompresses the base + z field
    >>> selection = laspy.DecompressionSelection.base().decompress_z()
    >>> selection.is_set(laspy.DecompressionSelection.Z)
    True
    >>> selection.is_set(laspy.DecompressionSelection.INTENSITY)
    False

    >>> # Creating a selection that decompresses all fields but the intensity
    >>> selection = laspy.DecompressionSelection.all().skip_intensity()
    >>> selection.is_set(laspy.DecompressionSelection.INTENSITY)
    False
    >>> selection.is_set(laspy.DecompressionSelection.Z)
    True


    .. versionadded:: 2.4

    """

    #: Flag to decompress x, y, return number, number of returns and scanner channel
    XY_RETURNS_CHANNEL = enum.auto()
    #: Flag to decompress z
    Z = enum.auto()
    #: Flag to decompress the classification
    CLASSIFICATION = enum.auto()
    #: Flag to decompress the classification flags (withheld, key point, overlap, etc)
    FLAGS = enum.auto()
    #: Flag to decompress the intensity
    INTENSITY = enum.auto()
    #: Flag to decompress the scan angle
    SCAN_ANGLE = enum.auto()
    #: Flag to decompress the user data
    USER_DATA = enum.auto()
    #: Flag to decompress the point source id
    POINT_SOURCE_ID = enum.auto()
    #: Flag to decompress the gps time
    GPS_TIME = enum.auto()
    #: Flag to decompress the red, green, blue
    RGB = enum.auto()
    #: Flag to decompress the nir
    NIR = enum.auto()
    #: Flag to decompress the wavepacket
    WAVEPACKET = enum.auto()
    #: Flag to decompress all the extra bytes
    ALL_EXTRA_BYTES = enum.auto()

    @classmethod
    def all(cls) -> "DecompressionSelection":
        """Returns a selection where all fields will be decompressed"""

        selection = cls.base()
        for flag in cls:
            selection = selection._set(flag)

        return selection

    @classmethod
    def base(cls) -> "DecompressionSelection":
        """
        Returns a decompression selection where only the base
        x, y, return number, number of returns and scanner channel will be decompressed
        """
        return cls.xy_returns_channel()

    @classmethod
    def xy_returns_channel(cls) -> "DecompressionSelection":
        """
        Returns a decompression selection where only the base
        x, y, return number, number of returns and scanner channel will be decompressed
        """
        return cls.XY_RETURNS_CHANNEL

    def to_lazrs(self) -> "lazrs.DecompressionSelection":
        import lazrs

        variant_mapping = {
            DecompressionSelection.XY_RETURNS_CHANNEL: lazrs.SELECTIVE_DECOMPRESS_XY_RETURNS_CHANNEL,
            DecompressionSelection.Z: lazrs.SELECTIVE_DECOMPRESS_Z,
            DecompressionSelection.CLASSIFICATION: lazrs.SELECTIVE_DECOMPRESS_CLASSIFICATION,
            DecompressionSelection.FLAGS: lazrs.SELECTIVE_DECOMPRESS_FLAGS,
            DecompressionSelection.INTENSITY: lazrs.SELECTIVE_DECOMPRESS_INTENSITY,
            DecompressionSelection.SCAN_ANGLE: lazrs.SELECTIVE_DECOMPRESS_SCAN_ANGLE,
            DecompressionSelection.USER_DATA: lazrs.SELECTIVE_DECOMPRESS_USER_DATA,
            DecompressionSelection.POINT_SOURCE_ID: lazrs.SELECTIVE_DECOMPRESS_POINT_SOURCE_ID,
            DecompressionSelection.GPS_TIME: lazrs.SELECTIVE_DECOMPRESS_GPS_TIME,
            DecompressionSelection.RGB: lazrs.SELECTIVE_DECOMPRESS_RGB,
            DecompressionSelection.NIR: lazrs.SELECTIVE_DECOMPRESS_NIR,
            DecompressionSelection.WAVEPACKET: lazrs.SELECTIVE_DECOMPRESS_WAVEPACKET,
            DecompressionSelection.ALL_EXTRA_BYTES: lazrs.SELECTIVE_DECOMPRESS_ALL_EXTRA_BYTES,
        }
        lazrs_selection = lazrs.SELECTIVE_DECOMPRESS_XY_RETURNS_CHANNEL
        for variant in DecompressionSelection:
            lazrs_selection |= variant_mapping[variant] if self.is_set(variant) else 0

        print(lazrs_selection)
        return lazrs.DecompressionSelection(lazrs_selection)

    def to_laszip(self) -> int:
        import laszip

        variant_mapping = {
            DecompressionSelection.XY_RETURNS_CHANNEL: laszip.DECOMPRESS_SELECTIVE_CHANNEL_RETURNS_XY,
            DecompressionSelection.Z: laszip.DECOMPRESS_SELECTIVE_Z,
            DecompressionSelection.CLASSIFICATION: laszip.DECOMPRESS_SELECTIVE_CLASSIFICATION,
            DecompressionSelection.FLAGS: laszip.DECOMPRESS_SELECTIVE_FLAGS,
            DecompressionSelection.INTENSITY: laszip.DECOMPRESS_SELECTIVE_INTENSITY,
            DecompressionSelection.SCAN_ANGLE: laszip.DECOMPRESS_SELECTIVE_SCAN_ANGLE,
            DecompressionSelection.USER_DATA: laszip.DECOMPRESS_SELECTIVE_USER_DATA,
            DecompressionSelection.POINT_SOURCE_ID: laszip.DECOMPRESS_SELECTIVE_POINT_SOURCE,
            DecompressionSelection.GPS_TIME: laszip.DECOMPRESS_SELECTIVE_GPS_TIME,
            DecompressionSelection.RGB: laszip.DECOMPRESS_SELECTIVE_RGB,
            DecompressionSelection.NIR: laszip.DECOMPRESS_SELECTIVE_NIR,
            DecompressionSelection.WAVEPACKET: laszip.DECOMPRESS_SELECTIVE_WAVEPACKET,
            DecompressionSelection.ALL_EXTRA_BYTES: laszip.DECOMPRESS_SELECTIVE_EXTRA_BYTES,
        }
        laszip_selection = laszip.DECOMPRESS_SELECTIVE_CHANNEL_RETURNS_XY
        for variant in DecompressionSelection:
            laszip_selection |= variant_mapping[variant] if self.is_set(variant) else 0

        return laszip_selection


def is_point_format_compressed(point_format_id: int) -> bool:
    compression_bit_7 = (point_format_id & 0x80) >> 7
    compression_bit_6 = (point_format_id & 0x40) >> 6
    if not compression_bit_6 and compression_bit_7:
        return True
    return False


def compressed_id_to_uncompressed(point_format_id: int) -> int:
    return point_format_id & 0x3F


def uncompressed_id_to_compressed(point_format_id: int) -> int:
    return (2**7) | point_format_id
