import abc
from typing import Any


class IPointReader(abc.ABC):
    """The interface to be implemented by the class that actually reads
    points from as LAS/LAZ file so that the LasReader can use it.

    It is used to manipulate LAS/LAZ (with different LAZ backends) in the
    reader
    """

    @property
    @abc.abstractmethod
    def source(self) -> Any:
        ...

    @abc.abstractmethod
    def read_n_points(self, n: int) -> bytearray:
        ...

    @abc.abstractmethod
    def seek(self, point_index: int) -> None:
        ...

    @abc.abstractmethod
    def close(self) -> None:
        ...
