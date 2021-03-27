""" All the custom exceptions types
"""


class LaspyError(Exception):
    pass


class UnknownExtraType(LaspyError):
    pass


class PointFormatNotSupported(LaspyError):
    pass


class FileVersionNotSupported(LaspyError):
    pass


class LazError(LaspyError):
    pass


class IncompatibleDataFormat(LaspyError):
    pass
