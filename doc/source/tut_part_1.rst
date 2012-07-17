Getting Started
===============

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

Once you successfully build and install the library, run the test suite to make sure everything is working:

    .. code-block:: sh
    
        $ python setup.py test


**Opening .LAS Files**

The first step for getting started with laspy is to open a :obj:`laspy.file.File`
object in read mode. As the file *"simple.las"* is included in the repository, 
the tutorial will refer to this data set. We will also assume that you're running
python from the root laspy directory; if you run from somewhere else you'll need
to change the path to simple.las.

The following short script does just this:

    .. code-block:: python 

        import numpy as np
        from laspy.file import File
        inFile = File("./laspytest/data/simple.las", mode = "r")

When a file is opened in read mode, laspy first reads the header, processess any
VLR and EVLR records, and then maps the point records with numpy. If no errors 
are produced when calling the File constructor, you're ready to read data!


**Reading Data**

Now you're ready to read data from the file. This can be header information, 
point data, or the contents of various VLR records. In general, point dimensions
are accessable as properties of the main file object, and header properties 
are accessable via the header property of the main file object. Refer to the 
background section of the tutorial for a reference of laspy dimension and field names. 

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

Again, the :obj:`laspy.file.File` object *inFile* has a reference
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
        for spec in inFile.point_format:
            print(spec.name)

        #Like XML or etree objects instead?
        a_mess_of_xml = pointformat.xml()
        an_etree_object = pointformat.etree()

        #It looks like we have color data in this file, so we can grab:
        blue = inFile.blue

        #Lets take a look at the header also. 
        headerformat = inFile.header.header_format
        for spec in headerformat:
            print(spec.name)




Now lets do something a bit more complicated. Say we're interested in grabbing
only the points from a file which are within a certain distance of the first point. 

    .. code-block:: python
    
        # Grab the scaled x, y, and z dimensions and stick them together 
        # in an nx3 numpy array

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


As you can see, having the data in numpy arrays is very convenient. Even better, 
it allows one to dump the data directly into any package with numpy/python bindings. 
For example, if you're interested in calculating the nearest neighbors of a set of points,
you might want to use a highly optimized package like FLANN (http://people.cs.ubc.ca/~mariusm/index.php/FLANN/FLANN)

Here's an example doing just this:

    .. code-block:: python
    
        from laspy.file import File
        import pyflann as pf
        import numpy as np

        # Open a file in read mode:
        inFile = File("./laspytest/data/simple.las")
        # Grab a numpy dataset of our clustering dimensions:
        dataset = np.vstack([inFile.X, inFile.Y, inFile.Z]).transpose()
        
        # Find the nearest 5 neighbors of point 100. 
        
        neighbors = flann.nn(dataset, dataset[100,], num_neighbors = 5)
        print("Five nearest neighbors of point 100: ")
        print(neighbors[0])
        print("Distances: ")
        print(neighbors[1])


Alternatively, one could use the built in KD-Tree functionality of scipy to do
nearest neighbor queries:

    .. code-block:: python

        from laspy.file import File
        from scipy.spatial.kdtree import KDTree
        import numpy as np

        # Open a file in read mode:
        inFile = File("./laspytest/data/simple.las")
        # Grab a numpy dataset of our clustering dimensions:
        dataset = np.vstack([inFile.X, inFile.Y, inFile.Z]).transpose()
        # Build the KD Tree
        tree = KDTree(data)
        # This should do the same as the FLANN example above, though it might
        # be a little slower.
        tree.query(dataset[100,], k = 5)



For another example, lets say we're interested only in the last return from each pulse in order to 
do ground detection. We can easily figure out which points are the last return by finding out for which points
return_num is equal to num_returns. 

    .. note::
        
        Unpacking a bit field like num_returns can be much slower than a whole byte, because
        the whole byte must be read by numpy and then converted in pure python. 

    .. code-block:: python

        # Grab the return_num and num_returns dimensions
        num_returns = inFile.num_returns
        return_num = inFile.return_num
        ground_points = inFile.points[num_returns == return_num]

        print("%i points out of %i were ground points." % (len(ground_points), 
                len(inFile)))
        

Since the data are simply returned as numpy arrays, we can use all sorts of 
analysis and plotting tools. For example, if you have matplotlib installed, you 
could quickly make a histogram of the intensity dimension:

    .. code-block:: python

        import matplotlib.pyplot as plt
        plt.hist(inFile.intensity)
        plt.title("Histogram of the Intensity Dimension")
        plt.show()

    .. image:: ./_static/tutorial_histogram.png 
        :width: 600

        


**Writing Data**

Once you've found your data subsets of interest, you probably want to store them somewhere. 
How about in new .LAS files?

When creating a new .LAS file using the write mode of :obj:`laspy.file.File`, 
we need to provide a :obj:`laspy.header.Header` instance, or a :obj:`laspy.header.HeaderManager` 
instance. We could instantiate a new instance without much input, but it will 
make potentially untrue assumptions about the point and file format. Luckily, we 
have a HeaderManager (which has a header) ready to go:

    .. code-block:: python
        
        outFile1 = File("./laspytest/data/close_points.las", mode = "w", 
                        header = inFile.header)
        outFile1.points = points_kept
        outFile1.close()

        outFile2 = File("./laspytest/data/ground_points.las", mode = "w", 
                        header = inFile.header)
        outFile2.points = ground_points
        outFile2.close()

That covers the basics of read and write mode. If, however, you'd like to modify
a las file in place, you can open it in read-write mode, as follows:

    .. code-block:: python
        
        inFile = File("./laspytest/data/close_points.las", mode = "rw")
        
        # Let's say the X offset is incorrect:
        old_location_offset = inFile.header.offset
        old_location_offset[0] += 100
        inFile.header.offset = old_location_offset

        # Lets also say our Y and Z axes are flipped. 
        Z = inFile.Z
        Y = inFile.Y
        inFile.Y = Z
        inFile.Z = Y

        # Enough changes, let's go ahead and close the file:
        inFile.close()


**Variable Length Records**

To create a VLR, you really only need to know user_id, record_id, and the data
you want to store in VLR_body (For a fuller discussion of what a VLR is, see the 
background section). The rest of the attributes are filled with null bytes
or calculated according to your input, but if you'd like to specify the reserved or 
description fields you can do so with additional arguments:

    .. code-block:: python
        
        # Import the :obj:`laspy.header.VLR` class.
        
        from laspy.file import File
        from laspy.header import VLR

        inFile = File("./laspytest/data/close_points.las", mode = "rw")
        # Instantiate a new VLR.
        new_vlr = VLR(user_id = "The User ID", record_id = 1, 
                      VLR_body = "\x00" * 1000)
        # Do the same thing without keword args
        new_vlr = VLR("The User ID", 1, "\x00" * 1000)
        # Do the same thing, but add a description field. 
        new_vlr = VLR("The User ID",1, "\x00" * 1000, 
                        description = "A decription goes here.")
        
        # Append our new vlr to the current list. As the above dataset is derived 
        # from simple.las which has no VLRS, this will be an empty list.
        old_vlrs = inFile.header.vlrs
        old_vlrs.append(new_vlr)
        inFile.header.vlrs = old_vlrs
        inFile.close()


**Putting it all together.**

Here is a collection of the code on this page, copypasta ready:


    .. code-block:: python 

        import numpy as np
        from laspy.file import File
        inFile = File("./laspytest/data/simple.las", mode = "r")
        # Grab all of the points from the file.
        point_records = inFile.points

        # Grab just the X dimension from the file, and scale it.
        def scaled_x_dimension(las_file):
            x_dimension = las_file.X
            scale = las_file.header.scale[0]
            offset = las_file.header.offset[0]
            return(x_dimension*scale + offset)
        scaled_x = scaled_x_dimension(inFile)

        # Find out what the point format looks like.
        print("Examining Point Format: ")
        pointformat = inFile.point_format
        for spec in inFile.point_format:
            print(spec.name)

        #Like XML or etree objects instead?
        print("Grabbing xml...")
        a_mess_of_xml = pointformat.xml()
        an_etree_object = pointformat.etree()

        #It looks like we have color data in this file, so we can grab:
        blue = inFile.blue

        #Lets take a look at the header also. 
        print("Examining Header Format:")
        headerformat = inFile.header.header_format
        for spec in headerformat:
            print(spec.name)

        print("Find close points...")
        # Grab the scaled x, y, and z dimensions and stick them together 
        # in an nx3 numpy array

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


        print("Find ground points...")
        # Grab the return_num and num_returns dimensions
        num_returns = inFile.num_returns
        return_num = inFile.return_num
        ground_points = inFile.points[num_returns == return_num]

        print("%i points out of %i were ground points." % (len(ground_points), 
                len(inFile)))
       
        
        print("Writing output files...")
        outFile1 = File("./laspytest/data/close_points.las", mode = "w", 
                        header = inFile.header)
        outFile1.points = points_kept
        outFile1.close()

        outFile2 = File("./laspytest/data/ground_points.las", mode = "w", 
                        header = inFile.header)
        outFile2.points = ground_points
        outFile2.close()


        print("Trying out read/write mode.")
        inFile = File("./laspytest/data/close_points.las", mode = "rw")
        
        # Let's say the X offset is incorrect:
        old_location_offset = inFile.header.offset
        old_location_offset[0] += 100
        inFile.header.offset = old_location_offset

        # Lets also say our Y and Z axes are flipped. 
        Z = inFile.Z
        Y = inFile.Y
        inFile.Y = Z
        inFile.Z = Y

        # Enough changes, let's go ahead and close the file:
        inFile.close()

        
        print("Trying out VLRs...")
        # Import the :obj:`laspy.header.VLR` class.
        
        from laspy.file import File
        from laspy.header import VLR

        inFile = File("./laspytest/data/close_points.las", mode = "rw")
        # Instantiate a new VLR.
        new_vlr = VLR(user_id = "The User ID", record_id = 1, 
                      VLR_body = "\x00" * 1000)
        # Do the same thing without keword args
        new_vlr = VLR("The User ID", 1, "\x00" * 1000)
        # Do the same thing, but add a description field. 
        new_vlr = VLR("The User ID",1, "\x00" * 1000, 
                        description = "A decription goes here.")
        
        # Append our new vlr to the current list. As the above dataset is derived 
        # from simple.las which has no VLRS, this will be an empty list.
        old_vlrs = inFile.header.vlrs
        old_vlrs.append(new_vlr)
        inFile.header.vlrs = old_vlrs
        inFile.close()

