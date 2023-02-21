import abc
import io
from typing import BinaryIO

from .header import LasHeader
from .point.record import PackedPointRecord


class IPointWriter(abc.ABC):
    """Interface to be implemented by the actual
    PointWriter backend

    """

    @property
    @abc.abstractmethod
    def destination(self) -> BinaryIO:
        ...

    @abc.abstractmethod
    def write_points(self, points: PackedPointRecord) -> None:
        ...

    @abc.abstractmethod
    def done(self) -> None:
        ...

    def write_initial_header_and_vlrs(
        self, header: LasHeader, encoding_errors: str
    ) -> None:
        header.write_to(self.destination, encoding_errors=encoding_errors)

    def write_updated_header(self, header: LasHeader, encoding_errors: str):
        self.destination.seek(0, io.SEEK_SET)
        header.write_to(
            self.destination, ensure_same_size=True, encoding_errors=encoding_errors
        )
