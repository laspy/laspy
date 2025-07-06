from setuptools import find_packages, setup

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
    packages=find_packages(exclude=("tests", "tests.cli")),
    python_requires=">=3.9",
    install_requires=["numpy"],
    extras_require={
        "dev": [
            "pytest",
            "coverage",
            "sphinx",
            "sphinx-rtd-theme",
            "nox",
            "attrs>=24.1",  # Needed for nox <= 2025.05.01 to work
            "black==22.3.0",
            "pytest-benchmark",
            "m2r2",
            "rangehttpserver",
            "isort==5.11.5",
        ],
        "lazrs": ["lazrs>=0.7.0, < 0.8.0"],
        "laszip": ["laszip >= 0.2.1, < 0.3.0"],
        "pyproj": ["pyproj"],
        "requests": ["requests"],
        "cli": [
            "typer[all] >= 0.8.0 ",
            "rich >= 10.11.0",
        ],
    },
    entry_points={
        "console_scripts": ["laspy=laspy.cli.main:main"],
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
