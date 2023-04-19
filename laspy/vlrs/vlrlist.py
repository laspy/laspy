import logging
from typing import BinaryIO, List

import numpy as np

from ..utils import read_string, write_as_c_string
from .known import IKnownVLR, vlr_factory
from .vlr import VLR

logger = logging.getLogger(__name__)

RESERVED_LEN = 2
USER_ID_LEN = 16
DESCRIPTION_LEN = 32


class VLRList(list):
    """Class responsible for managing the vlrs"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def index(self, value, start: int = 0, stop: int = None) -> int:
        if stop is None:
            stop = len(self)
        if isinstance(value, str):
            for i, vlr in enumerate(self[start:stop]):
                if vlr.__class__.__name__ == value:
                    return i + start
            raise ValueError(f"VLR '{value}' could not be found in the list")
        else:
            return super().index(value, start, stop)

    def get_by_id(self, user_id="", record_ids=(None,)):
        """Function to get vlrs by user_id and/or record_ids.
        Always returns a list even if only one vlr matches the user_id and record_id

        >>> import laspy
        >>> from laspy.vlrs.known import ExtraBytesVlr, WktCoordinateSystemVlr
        >>> las = laspy.read("tests/data/extrabytes.las")
        >>> las.vlrs
        [<ExtraBytesVlr(extra bytes structs: 5)>]
        >>> las.vlrs.get(WktCoordinateSystemVlr.official_user_id())
        []
        >>> las.vlrs.get(WktCoordinateSystemVlr.official_user_id())[0]
        Traceback (most recent call last):
        IndexError: list index out of range
        >>> las.vlrs.get_by_id(ExtraBytesVlr.official_user_id())
        [<ExtraBytesVlr(extra bytes structs: 5)>]
        >>> las.vlrs.get_by_id(ExtraBytesVlr.official_user_id())[0]
        <ExtraBytesVlr(extra bytes structs: 5)>

        Parameters
        ----------
        user_id: str, optional
                 the user id
        record_ids: iterable of int, optional
                    THe record ids of the vlr(s) you wish to get

        Returns
        -------
        :py:class:`list`
            a list of vlrs matching the user_id and records_ids

        """
        return [
            vlr
            for vlr in self
            if (user_id == "" or vlr.user_id == user_id)
            and (record_ids == (None,) or vlr.record_id in record_ids)
        ]

    def get(self, vlr_type: str) -> List[IKnownVLR]:
        """Returns the list of vlrs of the requested type
        Always returns a list even if there is only one VLR of type vlr_type.

        >>> import laspy
        >>> las = laspy.read("tests/data/extrabytes.las")
        >>> las.vlrs
        [<ExtraBytesVlr(extra bytes structs: 5)>]
        >>> las.vlrs.get("WktCoordinateSystemVlr")
        []
        >>> las.vlrs.get("WktCoordinateSystemVlr")[0]
        Traceback (most recent call last):
        IndexError: list index out of range
        >>> las.vlrs.get('ExtraBytesVlr')
        [<ExtraBytesVlr(extra bytes structs: 5)>]
        >>> las.vlrs.get('ExtraBytesVlr')[0]
        <ExtraBytesVlr(extra bytes structs: 5)>


        Parameters
        ----------
        vlr_type: str
                  the class name of the vlr

        Returns
        -------
        :py:class:`list`
            a List of vlrs matching the user_id and records_ids

        """
        return [v for v in self if v.__class__.__name__ == vlr_type]

    def extract(self, vlr_type: str) -> List[IKnownVLR]:
        """Returns the list of vlrs of the requested type
        The difference with get is that the returned vlrs will be removed from the list

        Parameters
        ----------
        vlr_type: str
                  the class name of the vlr

        Returns
        -------
        list
            a List of vlrs matching the user_id and records_ids

        """
        kept_vlrs, extracted_vlrs = [], []
        for vlr in self:
            if vlr.__class__.__name__ == vlr_type:
                extracted_vlrs.append(vlr)
            else:
                kept_vlrs.append(vlr)
        self.clear()
        self.extend(kept_vlrs)
        return extracted_vlrs

    def __repr__(self):
        return "[{}]".format(", ".join(repr(vlr) for vlr in self))

    @classmethod
    def read_from(
        cls, data_stream: BinaryIO, num_to_read: int, extended: bool = False
    ) -> "VLRList":
        """Reads vlrs and parse them if possible from the stream

        Parameters
        ----------
        data_stream : io.BytesIO
                      stream to read from
        num_to_read : int
                      number of vlrs to be read

        extended : bool
                      whether the vlrs are regular vlr or extended vlr

        Returns
        -------
        laspy.vlrs.vlrlist.VLRList
            List of vlrs

        """
        vlrlist = cls()
        for _ in range(num_to_read):
            data_stream.read(RESERVED_LEN)
            user_id = data_stream.read(USER_ID_LEN).split(b"\0")[0].decode()
            record_id = int.from_bytes(
                data_stream.read(2), byteorder="little", signed=False
            )
            if extended:
                record_data_len = int.from_bytes(
                    data_stream.read(8), byteorder="little", signed=False
                )
            else:
                record_data_len = int.from_bytes(
                    data_stream.read(2), byteorder="little", signed=False
                )
            description = read_string(data_stream, DESCRIPTION_LEN)
            record_data_bytes = data_stream.read(record_data_len)

            vlr = VLR(user_id, record_id, description, record_data_bytes)

            vlrlist.append(vlr_factory(vlr))

        return vlrlist

    def write_to(
        self,
        stream: BinaryIO,
        as_extended: bool = False,
        encoding_errors: str = "strict",
    ) -> int:
        bytes_written = 0
        for vlr in self:
            record_data = vlr.record_data_bytes()

            stream.write(b"\0\0")
            write_as_c_string(stream, vlr.user_id, USER_ID_LEN)
            stream.write(vlr.record_id.to_bytes(2, byteorder="little", signed=False))
            if as_extended:
                stream.write(
                    len(record_data).to_bytes(8, byteorder="little", signed=False)
                )
            else:
                max_length = np.iinfo("uint16").max
                if len(record_data) > max_length:
                    raise ValueError(
                        f"VLR record_date length ({len(record_data)}) exceeds the maximum length ({max_length})"
                    )
                stream.write(
                    len(record_data).to_bytes(2, byteorder="little", signed=False)
                )
            write_as_c_string(
                stream,
                vlr.description,
                DESCRIPTION_LEN,
                encoding_errors=encoding_errors,
            )
            stream.write(record_data)

            bytes_written += 54 if not as_extended else 60
            bytes_written += len(record_data)

        return bytes_written
