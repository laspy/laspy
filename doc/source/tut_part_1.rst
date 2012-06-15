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
        Laspy can actually scale the x, y, and z dimensions for you. Upper case dimensions 
        (*las_file.X, las_file.Y, las_file.Z*) give the raw integer dimensions, 
        while lower case dimensions (*las_file.x, las_file.y, las_file.z*) give 
        the scaled value. Both methods support assignment as well, although due to
        rounding error assignment using the scaled dimensions is not reccomended.

As you will have noticed, the :obj:`laspy.file.File` object *inFile* has a reference
to the :obj:`laspy.header.Header` object, which handles the getting and setting
of information stored in the laspy header record of *simple.las*. Notice also that 
the *scale* and *offset* values returned are actually lists of [*x scale, y scale, z scale*]
and [*x offset, y offset, z offset*] respectively.


LAS files differ in what data is available, and you may want to check out what the contents 
of your file are. Laspy includes several methods to document the file specification, 
based on the :obj:`laspy.util.Format` objects which are used to parse the file.

    .. code-block:: python

        # Find out what the point format looks like.
        pointformat = inFile.point_format
        for spec in inFile.point_format.specs:
            print(spec.name)

        #Like XML or etree objects instead?
        a_mess_of_xml = pointformat.xml()
        an_etree_object = pointformat.etree()

        #It looks like we have color data in this file, so we can grab:
        blue = inFile.blue

        #Lets take a look at the header also. 
        headerformat = inFile.header.header_format
        for spec in headerformat.specs:
            print(spec.name)

Now lets do something a bit more complicated. Say we're interested in grabbing
only the points from a file which are within a certain distance of the first point. 

    .. code-block:: python
    
        # Grab the scaled x, y, and z dimensions and stick them together in an nx3 numpy array

        coords = np.vstack((inFile.x, inFile.y, inFile.z)).transpose()

        # Pull off the first point
        first_point = coords[0,:]

        # Calculate the euclidean distance from all points to the first point

        distances = np.sum((coords - first_point)**2, axis = 1)

        # Create an array of indicators for whether or not a point is less than
        # 500000 units away from the first point

        keep_points = distances < 500000

        # Grab an array of all points which meet this threshold

        points_kept = inFile.points[keep_points]

        print("We're keeping %i points out of %i total"%(len(points_kept), len(inFile)))


Once you've found your data subset of interest, you probably want to store it somewher. 
How about in a new .LAS file?

When creating a new .LAS file using the write mode of :obj:`laspy.file.File`, 
we need to provide a :obj:`laspy.header.Header` instance. We could instantiate 
a new instance without much input, but it will make potentially untrue assumptions 
about the point and file format. Luckily, we have a header ready to go:

    .. code-block:: python
        
        outFile = File("./test/data/close_points.las", mode = "w", header = inFile.header)
        outFile.points = points_kept
        outFile.close()

That covers the basics of read and write mode. If, however, you'd like to modify
a las file in place, you can open it in read-write mode, as follows:

    .. code-block:: python
        
        inFile = File("./test/data/close_points.las", mode = "rw")
        
        # Let's say the offset is incorrect:
        old_offset = inFile.header.offset
        old_offset[0] += 100
        inFile.header.offset = old_offset

        # Lets also say our Y and Z axes are flipped. 
        Z = inFile.Z
        Y = inFile.Y
        inFile.Y = Z
        inFile.Z = Y

        # Enough changes, let's go ahead and close the file:
        inFile.close()



