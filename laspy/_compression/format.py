def is_point_format_compressed(point_format_id: int) -> bool:
    compression_bit_7 = (point_format_id & 0x80) >> 7
    compression_bit_6 = (point_format_id & 0x40) >> 6
    if not compression_bit_6 and compression_bit_7:
        return True
    return False


def compressed_id_to_uncompressed(point_format_id: int) -> int:
    return point_format_id & 0x3F


def uncompressed_id_to_compressed(point_format_id: int) -> int:
    return (2**7) | point_format_id
