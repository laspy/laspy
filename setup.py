
from glob import glob
from setuptools import setup

import laspy

# Get text from README.txt
#readme_text = file('docs/source/README.txt', 'rb').read()

    
setup(name          = 'laspy',
      version       = laspy.__version__,
      description   = 'Native Python ASPRS LAS read/write library',
      license       = 'BSD',
      keywords      = 'gis lidar las',
      author        = 'Grant Brown',
      author_email  = 'grant.brown73@gmail.com',
      maintainer        = 'Howard Butler',
      maintainer_email  = 'hobu@hobu.net',
      url   = 'https://github.com/grantbrown/laspy',
      long_description = '',
      packages      = ['laspy'],
      install_requires = ['numpy'],
      test_suite = 'test.test_laspy',
      data_files = None,
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

