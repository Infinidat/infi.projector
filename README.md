Overview
========

This is our python-based git project management.


Checking out the code
=====================

The easiest way to checkout the code is by using projector itself:

    easy_install infi.projector
    projector clone git://github.com/Infindiat/infi.projector.git
    cd infi.projector
    projector devenv build

There are two alternatives.

The first one using the environment python and requires you to install dependencies (it'll tell you what they are):

    python src/infi/projector/first_run/with_environment_python.py

The second does not modify the environment python, it uses only the buildout environment, and, it can be used with our isolated python build:

    python src/infi/projector/first_run/without_environment_python.py [--use-isolated-python]

