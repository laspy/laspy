from abc import ABC, abstractmethod
from typing import BinaryIO, Any, Optional

from .selection import DecompressionSelection
from .._pointappender import IPointAppender
from .._pointreader import IPointReader
from .._pointwriter import IPointWriter


class ILazBackend(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        ...

    @property
    @abstractmethod
    def supports_append(self) -> bool:
        ...

    @abstractmethod
    def create_appender(self, dest: BinaryIO, header: "LasHeader") -> IPointAppender:
        ...

    @abstractmethod
    def create_reader(
        self,
        source: Any,
        header: "LasHeader",
        decompression_selection: Optional[DecompressionSelection] = None,
    ) -> IPointReader:
        ...

    @abstractmethod
    def create_writer(
        self,
        dest: Any,
        header: "LasHeader",
    ) -> IPointWriter:
        ...
