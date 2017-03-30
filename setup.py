import shutil
from setuptools import setup

import laspy

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

with open('README.rst') as f:
    readme = f.read()

setup(name          = 'laspy',
      version       = laspy.__version__,
      description   = 'Native Python ASPRS LAS read/write library',
      license       = 'BSD',
      keywords      = 'gis lidar las',
      author        = 'Grant Brown',
      author_email  = 'grant.brown73@gmail.com',
      url   = 'https://github.com/laspy/laspy',
      long_description = readme,
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
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: GIS'
        ],
)

