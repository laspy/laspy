""" This module contains functions to pack and unpack point dimensions
"""
import numpy as np


def least_significant_bit_set(mask: int) -> int:
    """Return the least significant bit set

    The index is 0-indexed.
    Returns -1 is no bit is set

    >>> least_significant_bit_set(0b0000_0001)
    0
    >>> least_significant_bit_set(0b0001_0000)
    4
    >>> least_significant_bit_set(0b0000_0000)
    -1
    """
    return (mask & -mask).bit_length() - 1


def pack(array, sub_field_array, mask, inplace=False):
    """Packs a sub field's array into another array using a mask

    Parameters:
    ----------
    array : numpy.ndarray
        The array in which the sub field array will be packed into
    array_in : numpy.ndarray
        sub field array to pack
    mask : mask (ie: 0b00001111)
        Mask of the sub field
    inplace : {bool}, optional
        If true a new array is returned. (the default is False, which modifies the array in place)

    Raises
    ------
    OverflowError
        If the values contained in the sub field array are greater than its mask's number of bits
        allows
    """
    lsb = least_significant_bit_set(mask)
    max_value = int(mask >> lsb)
    if np.max(sub_field_array) > max_value:
        raise OverflowError(
            "value ({}) is greater than allowed (max: {})".format(
                sub_field_array.max(), max_value
            )
        )
    if inplace:
        array[:] = array & ~mask
        array[:] = array | ((sub_field_array << lsb) & mask).astype(array.dtype)
    else:
        array = array & ~mask
        return array | ((sub_field_array << lsb) & mask).astype(array.dtype)
