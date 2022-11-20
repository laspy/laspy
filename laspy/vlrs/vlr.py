from abc import ABC, abstractmethod
from typing import Union


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
    def description(self) -> Union[str, bytes]:
        ...

    @abstractmethod
    def record_data_bytes(self) -> bytes:
        ...


class BaseVLR(IVLR, ABC):
    def __init__(self, user_id, record_id, description=""):
        self._user_id: str = user_id
        self._record_id: int = record_id
        self._description: Union[str, bytes] = description

    @property
    def user_id(self) -> str:
        """
        The user id
        """
        return self._user_id

    @property
    def record_id(self) -> int:
        """
        The record id
        """
        return self._record_id

    @property
    def description(self) -> Union[str, bytes]:
        """
        The description, cannot exceed 32 bytes
        """
        return self._description


class VLR(BaseVLR):
    """
    >>> import laspy
    >>> my_vlr = laspy.VLR(
    ... user_id="MyUserId",
    ... record_id=0,
    ... description="An Example VLR",
    ... record_data=int(42).to_bytes(8, byteorder='little'),
    ... )
    >>> my_vlr.user_id
    'MyUserId'
    >>> int.from_bytes(my_vlr.record_data, byteorder='little')
    42
    """

    def __init__(self, user_id, record_id, description="", record_data=b""):
        super().__init__(user_id, record_id, description=description)
        #: The record_data as bytes, length cannot exceed 65_535
        self.record_data: bytes = record_data

    def record_data_bytes(self) -> bytes:
        return self.record_data

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
