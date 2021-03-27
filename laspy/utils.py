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
