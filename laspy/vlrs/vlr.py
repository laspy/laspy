from abc import ABC, abstractmethod
from typing import BinaryIO


class IVLR(ABC):
    @property
    @abstractmethod
    def user_id(self) -> str:
        ...

    @property
    @abstractmethod
    def record_id(self) -> int:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    def record_data_bytes(self) -> bytes:
        ...


class BaseVLR(IVLR, ABC):
    def __init__(self, user_id, record_id, description=""):
        self._user_id = user_id
        self._record_id = record_id
        self._description = description

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def record_id(self) -> int:
        return self._record_id

    @property
    def description(self) -> str:
        return self._description


class VLR(BaseVLR):
    def __init__(self, user_id, record_id, description="", record_data=b""):
        super().__init__(user_id, record_id, description=description)
        #: The record_data as bytes
        self.record_data = record_data

    def record_data_bytes(self) -> bytes:
        return self.record_data

    @classmethod
    def read_from(cls, stream: BinaryIO):
        stream.read(2)
        user_id = stream.read(16).decode().rstrip("\0")
        record_id = int.from_bytes(stream.read(2), byteorder="little", signed=False)
        description = stream.read(16).decode().rstrip("\0")
        record_length = int.from_bytes(stream.read(2), byteorder="little", signed=False)
        record_data = stream.read(record_length)
        vlr = cls(user_id, record_id, description, record_data)
        return vlr

    def __eq__(self, other):
        return (
            self.record_id == other.record_id
            and self.user_id == other.user_id
            and self.description == other.description
            and self.record_data == other.record_data
        )

    def __repr__(self):
        return "<{}(user_id: '{}', record_id: '{}', data len: {})>".format(
            self.__class__.__name__, self.user_id, self.record_id, len(self.record_data)
        )
