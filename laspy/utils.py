from typing import BinaryIO, Union


def encode_to_len(string: str, wanted_len: int, codec="ascii") -> bytes:
    encoded_str = string.encode(codec)

    missing_bytes = wanted_len - len(encoded_str)
    if missing_bytes < 0:
        raise ValueError(f"encoded str does not fit in {wanted_len} bytes")
    return encoded_str + (b"\0" * missing_bytes)


def encode_to_null_terminated(string: str, codec: str = "utf-8") -> bytes:
    b = string.encode(codec)
    if b[-1] != 0:
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


def write_string(
    stream: BinaryIO,
    string: Union[str, bytes],
    max_length: int,
    encoding: str = "ascii",
    encoding_errors: str = "strict",
) -> bool:
    """
    Writes the string or bytes to the stream.

    It will always write `max_length` bytes to the stream,
    so the input data may be null padded or truncated.
    """
    if isinstance(string, str):
        raw_bytes = string.encode(encoding, errors=encoding_errors)
    else:
        # check that the bytes are valid for the given encoding
        _ = string.decode(encoding, errors=encoding_errors)
        raw_bytes = string

    if len(raw_bytes) > max_length:
        stream.write(raw_bytes[:max_length])
        return True
    else:
        stream.write(raw_bytes.ljust(max_length, b"\0"))
        return False
