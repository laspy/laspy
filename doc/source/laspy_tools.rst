Laspy Tools
===========

Laspy comes with several command line utilities which use the library. When laspy 
is installed with setup.py, these scripts are built and installed by setuptools, 
and shold become available to the command line envionment you're using. The tools include
lascopy, lasexplorer, lasverify, and lasvalidate. These are the four full utilites 
provided by laspy at the moment, though other (less complete) code examples may 
be found in the laspy/misc directory.

**lascopy**

*overview*

Lascopy is a general purpose LAS file version and point format conversion
tool, and is able to read and write between all valid combinations of these two
values. If the output data format has fewer dimensions than the input data set, 
the output file will not include them.

*usage*
    For help, simply type:

    .. code-block:: sh
        
        lascopy -h

    In general, lascopy is called as:

    .. code-block:: sh
        
        lascopy ./path/to/input/file ./path/to/output/file <output point format> <output file format>

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
    result they are set to False by default. 
    
*example*

    Suppose you want to convert ./file_1.LAS to point format 8 from 0, and to
    file version 1.4 from 1.0. Further, suppose that you want to make sure 
    sub-byte fields are populated and that the histogram is updated. 
    You would call lascopy as:

    .. code-block:: sh
        
        lascopy ./file_1.LAS ./file_2.LAS 8 1.4 -u=True -b=True


    .. note::
        Even if -b=True is specified, lascopy may not be able to store all sub-byte
        data in the output format. This can occur when the input data has a larger
        number of bits per field. For example, las point formats 6-10 reserve
        four bits for return number, while formats 0-5 reserve only three. In 
        cases such as this, a larger value may be stored in the input file than 
        can be written to the output file. If this occurs, a warning is printed 
        and the output file receives zeros for the offending fields. 

**lasexplorer**

*Overview*

Lasexplorer is the simplest utility described here. It provides a basic entry
point to start an interactive shell to try out the laspy API. It accepts one
mandatory argument, the path to the file to be read. When run, the script reads
in the requested file, and calls the resulting laspy file object inFile. Unless suppressed, 
it also prints a brief summary of the LAS file supplied. 

*Usage*

The basic use case is simply:

    .. code-block:: sh
        
        lasexplorer ./path/to/las/file

The shell defaults to read mode, which will prevent you from accidentally breaking
any data files. If you want the ability to break stuff, however, you're free to specify 
the optional mode argument, and set it to read/write:

    .. code-block :: sh

        lasexplorer ./path/to/las/file -mode=rw

The shell doesn't provide the ability to open write mode files from the command
line, because this action requires a valid header object. If you'd like to experiment
with write mode, however, you can easily instantiate pure write mode files once
the shell is active:

    .. code-block :: python
        
        new_write_mode_file = File("Path_to_file.las", mode = "w", 
                                    header = inFile.header)

This is fine for learning how to use the API, but any substantial work is better
done with a dedicated script (see tutorial for details on scripting with laspy).

If you'd like to supress the printed summary, simply specify -q=True:
    
    .. code block :: sh
        
        python -i lasexplorer.py ./path/to/las/file -q=True

**lasvalidate**

*overview*

Lasvalidate is a simple validation tool for las files. Currently, it runs three tests though this may be expanded. 
First, it checks if all points fall inside the bounding box specified by file.header.max
and file.header.min. Second, it checks that the bounding box is precise, that is, 
that the max and min values specified by the header are equal to the max and min values
prensent in the point data within a given tolerance. Finally, it checks that the X
and Y range data makes sense. Lasvalidate produces a log file to indicate problems. 

*usage*

Lasvalidate is called as:

    .. code-block:: sh
        
        lasvalidate ./path/to/las/file

Optionally, the user can specify -log=/path/to/logfile and -tol=tolerance, where -log specifies
where the log will be written, and -tol determines the tolerance for comparisons of actual and header
max/min data. By default, the logfile is written to ./lasvalidate.log, and the tolerance is set to 0.01



        
**lasverify**

*overview*

Lasverify is a LAS file diff tool; that is, it compares two LAS files based on
header fields, point dimensons, and VLR/EVLR records. Header discrepencies are 
displayed, while differences in VLRs, EVLRs and point dimensons are simply indicated.

*usage*

In general, lasverify is called as:

    .. code-block:: sh 
        
        lasverify ./path/to/file/1 ./path/to/file/2

    There is one additional argument,-b, which is similar in function to its 
    counterpart in lascopy. Specifying -b=True will cause lasverify to dig into
    the sub-byte fields of both files to compare them individually in the case
    of a format mismatch, which occurrs when comparing files of point format
    less than six with those greater than five. Specifying -b=True when no such
    mismatch exists has no effect. 
