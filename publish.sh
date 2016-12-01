python setup.py register
python setup.py sdist --formats=gztar,zip upload
python setup.py bdist_wheel upload
python setup.py bdist_egg upload

