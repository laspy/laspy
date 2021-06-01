from . import errors


class File:
    def __init__(self, *args, **kwargs) -> None:
        raise errors.LaspyException(
            """laspy changed:
            To read a file do: las = laspy.read('somefile.laz')
            To create a new LAS data do: las = laspy.create(point_format=2, file_version='1.2')
            To write a file previously read or created: las.write('somepath.las')
            To stay on laspy 1.x: pip install laspy<2.0.0
            See the documentation for more information about the changes https://laspy.readthedocs.io/en/latest/"""
        )
