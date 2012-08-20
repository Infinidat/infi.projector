Overview
========

This is our python-based git project management.


Checking out the code
=====================

The easiest way to checkout the code is by using projector itself:

    easy_install infi.projector
    projector clone git://github.com/Infindiat/infi.projector.git
    cd infi.projector
    projector build scripts

If you don't want to install projector, or having trouble with the installation, you can do this:

    git clone git://github.com/Infinidat/infi.projector.git
    cd infi.projector
    git checkout -b develop origin/develop
    python first_run.py [--use-isolated-python]

