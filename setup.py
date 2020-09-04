from setuptools import setup

with open('README.md') as f:
    readme = f.read()

__version__ = None
# Get __version without importing
with open('laspy/__init__.py', 'r') as fp:
    # get and exec just the line which looks like "__version__ = '0.9.4'"
    exec(next(line for line in fp if '__version__' in line))

setup(name='laspy',
      version=__version__,
      description='Native Python ASPRS LAS read/write library',
      license='BSD',
      keywords='gis lidar las',
      author='Grant Brown',
      author_email='grant.brown73@gmail.com',
      url='https://github.com/laspy/laspy',
      long_description=readme,
      long_description_content_type='text/markdown',
      packages=['laspy', 'laspy.tools'],
      test_suite='test.test_laspy',
      data_files=[("test/data",
                  ["simple.las", "simple1_3.las",
                   "simple1_4.las", "simple.laz"])],
      install_requires=['numpy'],
      extras_require={
          "laz": 'lazperf ; platform_system!="Windows"'
          },
      include_package_data=True,
      zip_safe=False,
      entry_points={'console_scripts':
                    ['lascopy = laspy.tools.lascopy:main',
                     'lasexplorer = laspy.tools.lasexplorer:main',
                     'lasnoise = laspy.tools.lasnoise:main',
                     'lasverify = laspy.tools.lasverify:main',
                     'lasvalidate = laspy.tools.lasvalidate:main',
                     'lasviewer = laspy.tools.lasviewer:main'
                     ]},
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: GIS'
        ],
      )
