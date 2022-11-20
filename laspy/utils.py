from typing import BinaryIO, Union


def encode_to_null_terminated(string: str, codec: str = "utf-8") -> bytes:
    """
    >>> encode_to_null_terminated("las files are cool")
    b'las files are cool\\x00'

    >>> encode_to_null_terminated("")
    b'\\x00'
    """
    b = string.encode(codec)
    if not b or b[-1] != 0:
        b += b"\0"
    return b


def read_string(
    stream: BinaryIO, length: int, encoding: str = "ascii "
) -> Union[str, bytes]:
    """
    Reads `length` bytes from the stream, and tries to decode it.
    If the decoding succeeds, returns the `str`. Otherwise the raw bytes
    are returned.
    """
    raw_string = stream.read(length)
    first_null_byte_pos = raw_string.find(b"\0")
    if first_null_byte_pos >= 0:
        raw_string = raw_string[:first_null_byte_pos]

    try:
        return raw_string.decode(encoding)
    except UnicodeDecodeError:
        return raw_string


def write_as_c_string(
    stream: BinaryIO,
    string: Union[str, bytes],
    max_length: int,
    encoding: str = "ascii",
    encoding_errors: str = "strict",
) -> bool:
    """
    Writes the string or bytes as a 'C' string to the stream.

    A 'C' string is null terminated, so this function writes the null
    terminator.

    It will always write `max_length` bytes to the stream,
    so the input data may be null padded or truncated.
    """
    raw_bytes = get_bytes_from_string(string, encoding, encoding_errors)
    raw_bytes, was_truncated = null_pad_bytes(
        raw_bytes, max_length, null_terminate=True
    )
    stream.write(raw_bytes)

    return was_truncated


def write_string(
    stream: BinaryIO,
    string: Union[str, bytes],
    max_length: int,
    encoding: str = "ascii",
    encoding_errors: str = "strict",
) -> bool:
    """
    Writes the string or bytes as a 'C' string to the stream.

    Written data is not null terminated.

    It will always write `max_length` bytes to the stream,
    so the input data may be null padded or truncated.
    """
    raw_bytes = get_bytes_from_string(string, encoding, encoding_errors)
    raw_bytes, was_truncated = null_pad_bytes(
        raw_bytes, max_length, null_terminate=False
    )
    stream.write(raw_bytes)

    return was_truncated


def get_bytes_from_string(
    string: Union[str, bytes], encoding: str, encoding_errors: str
) -> bytes:
    if isinstance(string, str):
        raw_bytes = string.encode(encoding, errors=encoding_errors)
    else:
        # check that the bytes are valid for the given encoding
        _ = string.decode(encoding, errors=encoding_errors)
        raw_bytes = string

    return raw_bytes


def null_pad_bytes(
    raw_bytes: bytes, max_length: int, null_terminate: bool = True
) -> (bytes, bool):
    """
    Returns a byte string of `max_length` bytes.

    If the input bytes is shorter then the output will be null padded.

    If the input bytes is longer it will be truncated.

    If null_terminate is True, then the last byte is guaranteed to be a null
    byte (and the out string sill has `max_length` bytes).

    >>> null_pad_bytes(b'abcd', 5)
    (b'abcd\\x00', False)

    # input has 4 bytes, and must be 4 bytes long
    # but since null_terminate is True its guaranteed to be null terminated,
    # the last byte will be truncated
    >>> null_pad_bytes(b'abcd', 4)
    (b'abc\\x00', True)

    # Same setup, but don't null terminate
    >>> null_pad_bytes(b'abcd', 4, null_terminate=False)
    (b'abcd', False)

    >>> null_pad_bytes(b'abcdef', 4)
    (b'abc\\x00', True)

    >>> null_pad_bytes(b'abcdef', 4, null_terminate=False)
    (b'abcd', True)

    >>> null_pad_bytes(b'abcd', 10)
    (b'abcd\\x00\\x00\\x00\\x00\\x00\\x00', False)

    >>> null_pad_bytes(b'abcdabcd', 5)
    (b'abcd\\x00', True)

    >>> null_pad_bytes(b'abcde\\x00', 8)
    (b'abcde\\x00\\x00\\x00', False)

    >>> null_pad_bytes(b'abcde\\x00z', 8)
    (b'abcde\\x00\\x00\\x00', True)
    """
    was_truncated = False

    null_pos = raw_bytes.find(b"\0")
    if null_pos != -1:
        was_truncated = null_pos != len(raw_bytes) - 1
        raw_bytes = raw_bytes[:null_pos]

    if len(raw_bytes) >= max_length + (not null_terminate):
        raw_bytes = raw_bytes[: max_length - 1 + (not null_terminate)]
        was_truncated = True

    # This will effectively null pad
    raw_bytes = raw_bytes.ljust(max_length, b"\0")

    return raw_bytes, was_truncated
