The more complicated stuff
==========================


Using laspy's public api from :obj:`laspy.file.File` and :obj:`laspy.header.HeaderManager`
objects will get you a long way, but sometimes it's neccesary to dig a little deeper. 
For example, if you would like to build a 1.1 version file from a 1.2 version file, 
there is no automatic function to do this for you. Life becomes easier when we dig
into some of laspy's internal functionality:

    .. code-block:: python
        
        from laspy import file as File
        from laspy import header
        from laspy import util

        # Open an input file in read mode.
        inFile = File.File("./test/data/simple.las",mode= "r")

        # Use the get_copy method of HeaderManager objects to get a new low level
        # header instance. 
        new_header = inFile.header.get_copy()
        # Update the fields we want to change, the header format and pt_dat_format_id
        new_header.format = util.Format("h1.1")
        new_header.pt_dat_format_id = 0

        # Now we can create a new output file with our modified header.
        # Note that we need to give the file the VLRs manually, because the low level
        # header doesn't know about them, while the header manager does. 
        outFile = File.File("./test/data/output.las",mode= "w",vlrs = inFile.header.vlrs, header = new_header)

        # Iterate over all of the available point format specifications, attepmt to 
        # copy them to the new file. If we fail, print a message. 

        for dim in inFile.reader.point_format.specs:
            print("Copying dimension: " + dim.name)
            in_dim = inFile.reader.get_dimension(dim.name)
            try:
                outFile.writer.set_dimension(dim.name, in_dim)
            except(util.LaspyException):
                print("Couldn't set dimension: " + dim.name + 
                        " with file format " + str(outFile.header.version) + 
                        ", and point_format " + str(outFile.header.data_format_id))

        # Close the file

        outFile.close()
