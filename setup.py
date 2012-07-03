from setuptools import setup

import laspy

# Get text from README.txt
try:
    readme_text = file('README.rst', 'rb').read()
except:
    readme_text = "See documentation at www.laspy.org"

    
setup(name          = 'laspy',
      version       = laspy.__version__,
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
      packages      = ['laspy', 'laspytest'],
      install_requires = ['numpy'],
      test_suite = 'laspytest.test_laspy',
      data_files = [("laspytest/data", ["simple.las", "simple1_3.las", "simple1_4.las"])], 
      include_package_data = True,
      zip_safe = False,
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

