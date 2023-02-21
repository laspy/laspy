import abc

from .point.record import PackedPointRecord


class IPointAppender(abc.ABC):
    @abc.abstractmethod
    def append_points(self, points: PackedPointRecord) -> None:
        ...

    @abc.abstractmethod
    def done(self) -> None:
        ...
