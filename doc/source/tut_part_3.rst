New Features: LAS Versions 1.3 and 1.4
======================================

There is not a great deal of LAS version 1.3 and 1.4 test data around, so laspy's
implementation of these formats is neccesarily preliminary. Nevertheless, based
on the test data we've been able to find, all the basic features should work. 

The dimensions which are newly available from point formats 4-10 are accessed 
in the same way as those from formats 0-3. The tutorial background section has
an extensive list of what laspy calls each of these dimensions, but here we'll 
provide some quick examples. More examples can be found by looking at the 
./test/test_laspy.py file included in the source. 

**Opening Files**

Opening 1.3 and 1.4 files works exactly the same:

    .. code-block:: python

        import numpy as np
        from laspy.file import Files
        
        inFile_v13 = File("./test/data/simple1_3.las", mode = "r")
        inFile_v14 = File("./test/data/simple1_4.las", mode = "r")

**Reading Data - New Dimensions**
    
    .. code-block:: python
        
        #By checking the data_format_ids, we can see what new dimensions are present. 
        # Our 1.3 file has data format 4, and our 1.4 file has data format 7.
        inFile_v13.header.data_format_id
        inFile_v14.header.data_format_id
        
        #Grab some dimensons as usual:
        v_13 points = inFile_v13.points
        x_t = inFile_v13.x_t

        v_14_points = inFile_v14.points
        v_14_classification = inFile_v14.classification
        # Note that classification means different things depending on the file version.
        # Before v1.4, classification was part of the classification byte. This is 
        # called classification flags in 1.4, and classification refers to a new 
        # whole-byte field. For a discussion, see tutorial:background. 

**Writing Data + EVLRS**

EVLRS work very much the same way as traditional VLRs, though they are stored in
a different part of the file. 

    .. code-block:: python

        from laspy.header import EVLR
        outFile_14 = File("./test/data/output_14.las", mode = "w",
                        header = inFile_v14.header)
        new_evlr = EVLR(user_id = 10, record_id = 2, 
                        VLR_body = "Lots of data can go here.")
        #outFile_14 has the same, single EVLR as inFile
        old_evlrs = outFile_14.header.evlrs 
        old_evlrs.append(new_evlr)
        outFile_14.header.evlrs = old_evlrs
        outFile_14.close()

That covers the basics of new file manipulation, though this tutorial will be expanded
as development continues. 
        

        
