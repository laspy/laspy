import enum
from abc import ABCMeta
from typing import Any, BinaryIO, Optional, Tuple

from .._pointappender import IPointAppender
from .._pointreader import IPointReader
from .._pointwriter import IPointWriter
from .laszipbackend import LaszipBackend
from .lazbackend import ILazBackend
from .lazrsbackend import LazrsBackend
from .selection import DecompressionSelection

_DEFAULT_BACKENDS: Tuple[ILazBackend, ...] = (
    LazrsBackend(parallel=True),
    LazrsBackend(parallel=False),
    LaszipBackend(),
)


class ABCEnumMeta(enum.EnumMeta, ABCMeta):
    pass


# TODO: Replace the interactions with this class with interactions with ILazBackend classes
class LazBackend(ILazBackend, enum.Enum, metaclass=ABCEnumMeta):
    """Supported backends for reading and writing LAS/LAZ"""

    # type_hint = Union[LazBackend, Iterable[LazBackend]]

    LazrsParallel = 0
    """lazrs in multi-thread mode"""
    Lazrs = 1
    """lazrs in single-thread mode"""
    Laszip = 2
    """laszip backend"""

    def _get(self) -> ILazBackend:
        return _DEFAULT_BACKENDS[self.value]

    def is_available(self) -> bool:
        """Returns true if the backend is available"""
        for laz_backend in self.__class__:
            laz_backend: LazBackend
            if laz_backend == self:
                return self._get().is_available()
        return False

    @property
    def supports_append(self) -> bool:
        return self._get().supports_append

    def create_appender(self, dest: BinaryIO, header: "LasHeader") -> IPointAppender:
        return self._get().create_appender(dest, header)

    def create_reader(
        self,
        source: Any,
        header: "LasHeader",
        decompression_selection: Optional[DecompressionSelection] = None,
    ) -> IPointReader:
        return self._get().create_reader(
            source, header, decompression_selection=decompression_selection
        )

    def create_writer(
        self,
        dest: Any,
        header: "LasHeader",
    ) -> IPointWriter:
        return self._get().create_writer(dest, header)

    @classmethod
    def detect_available(cls) -> Tuple["LazBackend", ...]:
        """Returns a tuple containing the available backends in the current
        python environment
        """
        return tuple(
            laz_backend
            for backend, laz_backend in zip(_DEFAULT_BACKENDS, cls)
            if backend.is_available()
        )
