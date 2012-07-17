Laspy Tools
===========

Laspy comes with several command line utilities which use the library. In the 
laspy/tools directory, you should find lascopy.py and lasverify.py. These 
are the two full utilites provided by laspy at the moment, though other (less complete)
code examples may be found in the laspy/misc directory.

**lascopy**

*overview*

Lascopy is a general purpose LAS file version and point format conversion
tool, and is able to read and write between all valid combinations of these two
values. If the output data format has fewer dimensions than the input data set, 
the output file will not include them.

*usage*
    For help, simply type:

    .. code-block:: sh
        
        python lascopy.py -h

    In general, lascopy is called as:

    .. code-block:: sh
        
        python lascopy.py ./path/to/input/file ./path/to/output/file <output point format> <output file format>

    lascopy also accepts the optional logical arguments, -b and -u. 
    
    Specifying -b=True will cause lascopy to attempt to copy sub-byte field 
    data to the output file in the event that there is a discrepency in how 
    this data is stored between the two point formats (i.e., if you need to 
    convert between point formats 5 and below and  those greater than 5).

    Specifying -u=True indicates that lascopy should update the point return
    count histogram before closing the output file. This is usually not neccesary, 
    but when downscaling from point formats greater than 5 to point formats below
    5, there is excess point return data which can not fit into the header. 

    Both of these options are associated with substantial overhead, and as a 
    result they are False by default. 
    
*example*

    Suppose you want to convert ./file_1.LAS to point format 8 from 0, and to
    file version 1.4 from 1.0. Further, suppose that you want to make sure 
    sub-byte fields are populated and that the histogram is updated. 
    You would call lascopy as:

    .. code-block:: sh
        
        python lascopy.py ./file_1.LAS ./file_2.LAS 8 1.4 -u=True -b=True


    .. note::
        Even if -b=True is specified, lascopy may not be able to store all sub-byte
        data in the output format. This can occur when the input data has a larger
        number of bits per field. For example, las point formats 6-10 reserve
        four bits for return number, while formats 0-5 reserve only three. In 
        cases such as this, a larger value may be stored in the input file than 
        can be written to the output file. If this occurs, a warning is printed 
        and the output file receives zeros for the offending fields. 

**lasverify**

*overview*

Lasverify is a LAS file diff tool; that is, it compares two LAS files based on
header fields, point dimensons, and VLR/EVLR records. Header discrepencies are 
displayed, while differences in VLRs, EVLRs and point dimensons are simply indicated.

*usage*

In general, lasverify is called as:

    .. code-block:: sh 
        
        python lasverify.py ./path/to/file/1 ./path/to/file/2

    There is one additional argument,-b, which is similar in function to its 
    counterpart in lascopy. Specifying -b=True will cause lasverify to dig into
    the sub-byte fields of both files to compare them individually in the case
    of a format mismatch, which occurrs when comparing files of point format
    less than six with those greater than five. Specifying -b=True when no such
    mismatch exists has no effect. 
