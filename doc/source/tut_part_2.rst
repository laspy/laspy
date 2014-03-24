The more complicated stuff
==========================


Using laspy's public api from :obj:`laspy.file.File` and :obj:`laspy.header.HeaderManager`
objects will get you a long way, but sometimes it's neccesary to dig a little deeper. 
For example, if you would like to build a 1.1 version file from a 1.2 version file, 
there is no automatic function to do this for you. Life becomes easier when we dig
into some of laspy's internal functionality:

    .. code-block:: python

        import laspy        
        import copy

        # Open an input file in read mode.
        inFile = laspy.file.File("./laspytest/data/simple.las",mode= "r")

        # Call copy on the HeaderManager object to get a more portable Header instance.
        # This means we don't  have to modify the header on the read mode inFile. 
        new_header = copy.copy(inFile.header)
        # Update the fields we want to change, the header format and data_format_id
        new_header.format = 1.1
        new_header.pt_dat_format_id = 0

        # Now we can create a new output file with our modified header.
        # Note that we need to give the file the VLRs manually, because the low level
        # header doesn't know about them, while the header manager does. 
        outFile = laspy.file.File("./laspytest/data/output.las",
                            mode= "w",
                            vlrs = inFile.header.vlrs, 
                            header = new_header)

        # Iterate over all of the available point format specifications, attepmt to 
        # copy them to the new file. If we fail, print a message. 
        
        # Take note of the get_dimension and set_dimension functions. These are
        # useful for automating dimension oriented tasks, because they just require
        # the spec name to do the lookup. 

        for spec in inFile.reader.point_format:
            print("Copying dimension: " + spec.name)
            in_spec = inFile.reader.get_dimension(spec.name)
            try:
                outFile.writer.set_dimension(spec.name, in_spec)
            except(util.LaspyException):
                print("Couldn't set dimension: " + spec.name + 
                        " with file format " + str(outFile.header.version) + 
                        ", and point_format " + str(outFile.header.data_format_id))

        # Close the file

        outFile.close()
