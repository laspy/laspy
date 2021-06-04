import numpy as np

from . import errors

_extra_dims_base = (
    "u1",
    "i1",
    "u2",
    "i2",
    "u4",
    "i4",
    "u8",
    "i8",
    "f4",
    "f8",
)

_allowed_extra_dims_types = []
_allowed_extra_dims_types.extend(np.dtype(base) for base in _extra_dims_base)
for i in (2, 3):
    _allowed_extra_dims_types.extend(
        np.dtype(f"{i}{base}") for base in _extra_dims_base
    )
_allowed_extra_dims_types = tuple(_allowed_extra_dims_types)


def get_dtype_for_extra_dim(type_index: int) -> np.dtype:
    """Returns the dtype for the given type index

    Note that 0 is a special case not handled by this

    Parameters
    ----------
    type_index: int
        index of the type as defined in the LAS Specification

    Returns
    -------
    str,
        a string representing the type, can be understood by numpy

    """
    assert type_index != 0, "Can't get np.dtype for type_index 0"
    try:
        return _allowed_extra_dims_types[type_index - 1]
    except IndexError:
        raise errors.UnknownExtraType(type_index) from None


def get_id_for_extra_dim_type(dtype: np.dtype) -> int:
    """Returns the index of the type as defined in the LAS Specification

    Parameters
    ----------
    dtype: str

    Returns
    -------
    int
        index of the type

    """
    try:
        return _allowed_extra_dims_types.index(dtype) + 1
    except ValueError:
        raise errors.UnknownExtraType(dtype) from None
