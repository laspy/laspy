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
