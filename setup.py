from setuptools import setup
import shutil

# Get text from README.txt
try:
    readme_text = file('README.rst', 'rb').read()
except:
    readme_text = "See documentation at www.laspy.org"

# Make sure test data files are in the right place. There's probably a better 
# way to do this, but it should work. 

try:
    tmpFile = open("simple.las")
    tmpFile.close()
    tmpFile = open("simple1_3.las")
    tmpFile.close()
    tmpFile = open("simple1_4.las")
    tmpFile.close()
    tmpFile = open("simple.laz")
    tmpFile.close()
except:
    shutil.copyfile("laspytest/data/simple.las", "simple.las")
    shutil.copyfile("laspytest/data/simple1_3.las", "simple1_3.las")
    shutil.copyfile("laspytest/data/simple1_4.las", "simple1_4.las")
    shutil.copyfile("laspytest/data/simple.laz", "simple.laz")

    
setup(name          = 'laspy',
      version       = '1.4.2',
      description   = 'Native Python ASPRS LAS read/write library',
      license       = 'BSD',
      keywords      = 'gis lidar las',
      author        = 'Grant Brown',
      author_email  = 'grant.brown73@gmail.com',
      url   = 'https://github.com/grantbrown/laspy',
      long_description = '''Laspy is a python library for reading, writing, and 
                        modifying .LAS LIDAR files. It provides both a dimension 
                        and point focused API. Documentation is available at 
                        www.laspy.org, and the source is available at 
                        www.github.com/grantbrown/laspy''',
      packages      = ['laspy', 'laspytest','laspy.tools'],
      install_requires = ['numpy'],
      test_suite = 'laspytest.test_laspy',
      data_files = [("laspytest/data", ["simple.las", "simple1_3.las", "simple1_4.las", "simple.laz"])], 
      include_package_data = True,
      zip_safe = False,
      entry_points = {'console_scripts':['lascopy = laspy.tools.lascopy:main',
                                         'lasexplorer = laspy.tools.lasexplorer:main',
                                         'lasnoise = laspy.tools.lasnoise:main',
                                         'lasverify = laspy.tools.lasverify:main',
                                         'lasvalidate = laspy.tools.lasvalidate:main',
                                         'lasviewer = laspy.tools.lasviewer:main'
                                        ]},

      classifiers   = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: GIS'
        ],
)

