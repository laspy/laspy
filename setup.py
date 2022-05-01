from setuptools import setup, find_packages

with open("README.md") as f:
    readme = f.read()

__version__ = None
# Get __version without importing
with open("laspy/__init__.py", "r") as fp:
    # get and exec just the line which looks like "__version__ = '0.9.4'"
    exec(next(line for line in fp if "__version__" in line))

setup(
    name="laspy",
    version=__version__,
    description="Native Python ASPRS LAS read/write library",
    license="BSD",
    keywords="gis lidar las",
    author="Grant Brown, Thomas Montaigu",
    author_email="grant.brown73@gmail.com, thomas.montaigu@laposte.net",
    url="https://github.com/laspy/laspy",
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=("tests",)),
    python_requires=">=3.7",
    install_requires=["numpy"],
    extras_require={
        "dev": [
            "pytest",
            "sphinx",
            "sphinx-rtd-theme",
            "nox",
            "black==22.3.0",
            "pytest-benchmark",
            "m2r2",
        ],
        "lazrs": ["lazrs>=0.4.0, < 0.5.0"],
        "laszip": ["laszip >= 0.1.0, < 0.2.0"],
        "pyproj": ["pyproj"],
    },
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering :: GIS",
    ],
)
