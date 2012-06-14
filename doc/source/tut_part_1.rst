Getting Started
===============

**LAS Specifications**
Currently, laspy supports LAS formats 1.0 to 1.2, although support for 1.3 formatted files
is a definite next step. The various LAS specifications are available below:

http://www.asprs.org/a/society/committees/standards/asprs_las_format_v10.pdf 
http://www.asprs.org/a/society/committees/standards/asprs_las_format_v11.pdf 
http://www.asprs.org/a/society/committees/standards/asprs_las_format_v12.pdf 
http://www.asprs.org/a/society/committees/standards/asprs_las_spec_v13.pdf

**Dependencies**

Apart from the python standard library, we require Numpy, available at http://numpy.scipy.org.

**Installation**

If you feel comfortable manually installing python libraries, feel free to do so - 
the module is readily importable from ./laspy/, so adding this directory to your
sys.path should suffice. Otherwise, the easiest way to get set up is to use setuptools or distribute. 

Distribute is available at: http://pypi.python.org/pypi/distribute.

Once you have that installed, navigate to the root laspy directory where setup.py is located, and do: 
    .. code-block:: sh 

        $ python setup.py build
        $ python setup.py install

If you encounter permissions errors at this point (and if you're using a unix environment)
you may need to run the above comands as root, e.g. 
    
    .. code-block:: sh 
    
        $ sudo python setup.py build

Once you successfully build and install the library, run the test suite to make sure everythingis working:

    .. code-block:: sh
    
        $ python setup.py test


**Reading in Files**

The first step for getting started with laspy is to open a :obj:`laspy.file.File`
object in read mode. As the file *"simple.las"* is included in the repository, 
the tutorial will refer to this data set. We will also assume that you're running
python from the root laspy directory; if you run from somewhere else you'll need
to change the path to simple.las.

The following short script does just this:

    .. code-block:: python 

        import numpy as np
        from laspy.file import File
        inFile = File("./test/data/simple.las", mode = "r")

Now you're ready to read data from the file. This can be header information, 
point data, or the contents of various VLR records:

    .. code-block:: python
       
        # Grab all of the points from the file.
        point_records = inFile.points

        # Grab just the X dimension from the file, and scale it.
        
        def scaled_x_dimension(las_file):
            x_dimension = las_file.X
            scale = las_file.header.scale[0]
            offset = las_file.header.offset[0]
            return(x_dimension*scale + offset)

        scaled_x = scaled_x_dimension(inFile)

    .. note::
        Auto scaling of dimensions is on the laspy to do list, but the example 
        is still illustrative.

As you will have noticed, the :obj:`laspy.file.File` object *inFile* has a reference
to the :obj:`laspy.header.Header` object, which handles the getting and setting
of information stored in the laspy header record of *simple.las*. Notice also that 
the *scale* and *offset* values returned are actually lists of [*x scale, y scale, z scale*]
and [*x offset, y offset, z offset*] respectively.
        

        
