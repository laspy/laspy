New Format Features: LAS Versions 1.3 and 1.4
=============================================

There is not a great deal of LAS version 1.3 and 1.4 test data around, so laspy's
implementation of these formats is neccesarily preliminary. Nevertheless, based
on the test data we've been able to find, all the basic features should work. 

The dimensions which are newly available from point formats 4-10 are accessed 
in the same way as those from formats 0-3. The tutorial background section has
an extensive list of what laspy calls each of these dimensions, but here we'll 
provide some quick examples. More examples can be found by looking at the 
./test/test_laspy.py file included in the source. 

Additionally, LAS version 1.4 provides the ability to specify an "extra bytes"
variable length record (or EVLR) which can dynamically add additional dimensins. 
Laspy now parses such records, and provides the specified dimensions accordingly. 

The names of these new dimensions are constructed by using the name field specified
in the VLR record, and replacing null bytes with python empty strings, spaces with 
underscores, and upper case letters with lower case letters. For example, the field

    "Pulse Width\\X00\\X00\\X00\\X00\\X00\\X00\\X00\\X00\\X00"


would become simply: "pulse_width"

In order to maintain backwards compatability, laspy also provides access to these 
dimensions via :obj:`laspy.file.extra_bytes`, which provides raw access to the 
extra bytes in point records (present when data_record_length is greater than 
the default for a given point format).

**Opening Files**

Opening 1.3 and 1.4 files works exactly the same:

    .. code-block:: python

        import numpy as np
        import laspy
        
        inFile_v13 = laspy.file.File("./laspytest/data/simple1_3.las", mode = "r")
        inFile_v14 = laspy.file.File("./laspytest/data/simple1_4.las", mode = "r")

**Reading Data - New Dimensions**
    
    .. code-block:: python
        
        #By checking the data_format_ids, we can see what new 
        # dimensions are present. Our 1.3 file has data format 4, 
        # and our 1.4 file has data format 7.
        inFile_v13.header.data_format_id
        inFile_v14.header.data_format_id
        
        #Grab some dimensions as usual:
        v_13 points = inFile_v13.points
        x_t = inFile_v13.x_t

        v_14_points = inFile_v14.points
        v_14_classification = inFile_v14.classification
        
        # Note that classification means different things depending on 
        # the file version. Before v1.4, classification was part of the 
        # classification byte. This is called classification flags in 1.4, 
        # and classification refers to a new whole-byte field. For a 
        # discussion, see tutorial:background. 

**Writing Data + EVLRS**

EVLRS work very much the same way as traditional VLRs, though they are stored in
a different part of the file. 

    .. code-block:: python

        import laspy
        outFile_14 = laspy.file.File("./laspytest/data/output_14.las", mode = "w",
                        header = inFile_v14.header)
        new_evlr = laspy.header.EVLR(user_id = 10, record_id = 2, 
                        VLR_body = "Lots of data can go here.")
        #outFile_14 has the same, single EVLR as inFile
        old_evlrs = outFile_14.header.evlrs 
        old_evlrs.append(new_evlr)
        outFile_14.header.evlrs = old_evlrs
        outFile_14.close()


**Extra Bytes**

The extra bytes in a point record can now be described by a particular type of VLR.
From the LAS 1.4 specification, a VLR which describes new dimensions should have the 
following header information:

    User ID:  LASF_Spec

    Record ID:  4 
    
    Record Length after Header: n x 192 bytes

where n is the number of new dimensions that the VLR will define. The actual dimension
specification goes in the body of the VLR, and has the following structure:

.. note::
    Laspy coerces the no_data, max and min fields to have double precision format. 
    If this is a problem for your application, let us know. 


*Extra Bytes Struct*

============ ==============================
 Name        Format[number] (Total Bytes)
============ ==============================
 reserved     unsigned char[2] (2)
 data_type    unsigned char[1] (1)
 options      unsigned char[1] (1)
 name         char[32] (32)
 unused       char[4] (4)
 no_data      double[3] (24)
 min          double[3] (24)
 max          double[3] (24)
 scale        scale[3] (24)
 offset       offset[3] (24)
 description  char[32] (24)
============ ==============================

*Data Type Description*

======= ========================= ===================
 Value   Meaning                   Size
======= ========================= ===================
 0       Raw Extra Bytes           Value of "options" 
 1       unsigned char             1 byte 
 2       Char                      1 byte 
 3       unsigned short            2 bytes 
 4       Short                     2 bytes 
 5       unsigned long             4 bytes 
 6       Long                      4 bytes 
 7       unsigned long long        8 bytes 
 8       long long                 8 bytes 
 9       Float                     4 bytes 
 10      Double                    8 bytes 
 11      unsigned char[2]          2 byte 
 12      char[2]                   2 byte 
 13      unsigned short[2]         4 bytes 
 14      short[2]                  4 bytes 
 15      unsigned long[2]          8 bytes 
 16      long[2]                   8 bytes 
 17      unsigned long long[2]     16 bytes 
 18      long long[2]              16 bytes 
 19      float[2]                  8 bytes 
 20      double[2]                 16 bytes 
 21      unsigned char[3]          3 byte
 22      char[3]                   3 byte 
 23      unsigned short[3]         6 bytes 
 24      short[3]                  6 bytes
 25      unsigned long[3]          12 bytes 
 26      long[3]                   12 bytes 
 27      unsigned long long[3]     24 bytes 
 28      long long[3]              24 bytes 
 29      float[3]                  12 bytes 
 30      double[3]                 24 bytes

======= ========================= ===================

**Adding Extra Dimensions - The laspy way.** 

One can easily create new dimensions using the above data type table
and a laspy file object. In fact, it is not even neccesary to use a 1.4 file 
in this process, however other software will likely not know to use the new
1.4 features in a previous file version. Most readers should, however, 
be able to treat the extra dimensions as extra bytes. Here's the easy way to specify new dimensions:


    .. code-block:: python
        
        import laspy

        # Set up our input and output files.
        inFile = laspy.file.File("./laspytest/data/simple.las", mode = "r")
        outFile = laspy.file.File("./laspytest/data/output.las", mode = "w", 
                    header = inFile.header)
        # Define our new dimension. Note, this must be done before giving 
        # the output file point records.
        outFile.define_new_dimension(name = "my_special_dimension", 
                                data_type = 5, description = "Test Dimension")
        
        # Lets go ahead and copy all the existing data from inFile:
        for dimension in inFile.point_format:
            dat = inFile.reader.get_dimension(dimension.name)
            outFile.writer.set_dimension(dimension.name, dat)

        # Now lets put data in our new dimension 
        # (though we could have done this first)

        # Note that the data type 5 refers to a long integer
        outFile.my_special_dimension = range(len(inFile))
        

**Adding Extra Dimensions - The long way.**

If you want to see what's happening when you create new dimensions at a level 
much closer to the raw specification, laspy lets you create the requisite components manually. 

    .. code-block:: python

        import laspy  
        import copy

        inFile = laspy.file.File("./laspytest/data/simple.las", mode = "r")
        
        # We need to build the body of our dimension VLRs, and to do this we 
        # will use a class called ExtraBytesStruct. All we really need to tell
        # it at this point is the name of our dimension and the data type. 

        extra_dimension_spec_1 = laspy.header.ExtraBytesStruct(name = "My Super Special Dimension",
                                                               data_type = 5)
        extra_dimension_spec_2 = laspy.header.ExtraBytesStruct(name = "Another Special Dimension",
                                                               data_type = 5)
        vlr_body = (extra_dimension_spec_1.to_byte_string() + 
                   extra_dimension_spec_2.to_byte_string())

        # Now we can create the VLR. Note the user_id and record_id choices. 
        # These values are how the LAS specification determines that this is an 
        # extra bytes record. The description is just good practice. 
        extra_dim_vlr = laspy.header.VLR(user_id = "LASF_Spec",
                                         record_id = 4, 
                                         description = "Testing Extra Bytes.", 
                                         VLR_body = vlr_body)
             

        # Now let's put together the header for our new file. We need to increase
        # data_record_length to fit our new dimensions. See the data_type table 
        # for details. We also need to change the file version
        new_header = copy.copy(inFile.header)
        new_header.data_record_length += 8
        new_header.format = 1.4

        # Now we can create the file and give it our VLR.
        new_file = laspy.file.File("./laspytest/data/new_14_file.las", mode = "w", 
                        header = new_header, vlrs = [extra_dim_vlr])
        
        # Let's copy the existing data:
        for dimension in inFile.point_format:
            dim = inFile._reader.get_dimension(dimension.name)
            new_file._writer.set_dimension(dimension.name, dim)

        # We should be able to acces our new dimensions based on the 
        # Naming convention described above. Let's put some dummy data in them.
        new_file.my_super_special_dimension = [0]*len(new_file)
        new_file.another_special_dimension = [10]*len(new_file)
        
        # If we would rather grab a raw byte representation of all the extra 
        # dimensions, we can use:

        raw_bytes = new_file.extra_bytes

        # This might be useful if we wanted to later take this data and put it
        # back into an older file version which doesn't support extra dimensions.
