from typing import BinaryIO, Union


def encode_to_len(string: str, wanted_len: int, codec="ascii") -> bytes:
    encoded_str = string.encode(codec)

    missing_bytes = wanted_len - len(encoded_str)
    if missing_bytes < 0:
        raise ValueError(f"encoded str does not fit in {wanted_len} bytes")
    return encoded_str + (b"\0" * missing_bytes)


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
    if isinstance(string, str):
        raw_bytes = string.encode(encoding, errors=encoding_errors)
    else:
        # check that the bytes are valid for the given encoding
        _ = string.decode(encoding, errors=encoding_errors)
        raw_bytes = string

    raw_bytes, was_truncated = null_terminate_and_pad(raw_bytes, max_length)
    stream.write(raw_bytes)

    return was_truncated


def null_terminate_and_pad(raw_bytes: bytes, max_length: int) -> (bytes, bool):
    """
    Returns null-terminated bytes of exactly `max_length` long.

    The bytes are null padded (at the end) if the `len(raw_bytes) < max_length`.

    If the input raw bytes are longer that `max_length - 1` (account for the null-terminator)
    then the data will be truncated

    >>> null_terminate_and_pad(b'abcd', 5)
    (b'abcd\\x00', False)

    # input has 4 bytes, and must be 4 bytes long
    # but since its guaranteed to be null terminated,
    # the last byte will be truncated
    >>> null_terminate_and_pad(b'abcd', 4)
    (b'abc\\x00', True)

    >>> null_terminate_and_pad(b'abcd', 10)
    (b'abcd\\x00\\x00\\x00\\x00\\x00\\x00', False)

    >>> null_terminate_and_pad(b'abcdabcd', 5)
    (b'abcd\\x00', True)

    >>> null_terminate_and_pad(b'abcde\\x00', 8)
    (b'abcde\\x00\\x00\\x00', False)

    >>> null_terminate_and_pad(b'abcde\\x00z', 8)
    (b'abcde\\x00\\x00\\x00', True)
    """
    was_truncated = False

    null_pos = raw_bytes.find(b"\0")
    if null_pos != -1:
        was_truncated = null_pos != len(raw_bytes) - 1
        raw_bytes = raw_bytes[:null_pos]

    if len(raw_bytes) >= max_length:
        raw_bytes = raw_bytes[: max_length - 1]
        was_truncated = True

    # This will effectively null terminate/null pad
    raw_bytes = raw_bytes.ljust(max_length, b"\0")

    return raw_bytes, was_truncated
