Overview
========

Projector helps you set up isolated environments for developing Python projects, and pack these environment into isolated packages that you can later install on production.

At Infinidat, we build software for system administrators, that expect a complete, packaged product, and not just a bunch of Python scripts. Since Python (at least until Python 3.2) does not provide a decent mechanism for building Python applications (with a bundled interpreter), we started building our own solution, and this is what we came up with.

By using some skeleton, `buildout` recipes and some wrapping code, we provide:

* Isolated python builds for your applications
* Simple, easy-to-use version release mechanism
* Packaging Python applications into MSI, RPM, DEB

Using Projector
===============

Installation
------------

Projector is available on `pypi.python.org`, as `infi.projector`. To install just run:

    easy_install -U infi.projector


Walkthrough
-----------

We will explain the bits and bolts about using project by a straight-forward walkthrough.


### Creating a new project

We will start by creating a new project:

    projector repository init --mkdir infi.example git@github.com:Infinidat/example.git "example on infi.projector" "An example by walkthrough"

This creates a new skeleton for the project, under a new directory, called infi.example`. Inside, you'll find the following files:

* `bootstrap.py`. This file is buildout's boot strapper, used to start building the development environment
* `buildout.cfg`. This project's configuration file. Already includes the project name and description strings.
* `buildout.in`.  Yet another configuration file, used in production environments.
* `setup.in`.     A template file for setup.py. Modify when necessary.

Also, you'll notice that the checked out branch is `develop`. That is because we use `gitflow`'s branching model. That means that `master` holds merges for final releases only, and that the development is on `develop` or separate feature branches.

### Building the development environment

If you just create a new project, or clone an existing one, you won't have a proper setup.py, or any console script. In order to generate those, run:

    projector devenv build

This script will create the buildout environment, generate the version files from Git, and create the executable scripts under the `bin` directory.

If you want to use our isolated python builds in our development environment, and not the global Python, run instead:

    projector devenv build --isolated-python

This will download the platform-specific build from our servers, and use that.

There are other flags for this command, you can read about them by passing `--help`.

Some environment variables may change the behavior of the build process. Specifically, `PROJECTOR_BOOTSTRAP_DOWNLOAD_BASE` and `PROJECTOR_BOOTSTRAP_SETUP_SOURCE` change
the command-line parameters passed to `bootstrap.py` (`--download-base` and `--setup-source`, respectively).

### Adding dependencies

Projects handled by `projector` have two types of dependencies:

* `production` dependencies. written to setup.py, honored by `pip`/`easy_install`
* `development` dependencies. written to buildout.cfg, affects only the development environment.

Handling both types of dependencies/requirements is easy:

    projector requirements list [--development]
    projector requirements add <requirement> [--development] [--commit-changes]
    projector requirements remove <requirement> [--development] [--commit-changes]

#### Freezing versions

You can `freeze` the development environment by using the following commands:

    projector requirements freeze [--with-install-requires] [--commit-changes] [--newest]
    projector requirements unfreeze [--with-install-requires] [--commit-changes]

What this does is adds the versions of the downloaded dependencies to `buildout.cfg`, so that you'll always get the same set of dependencies when you run `devenv build`.

If you pass the `--with-install-requires` flag, this will also update the dependencies in `install_requires` with a `>=` requirement to the locally installed version.

### Console scripts

`projector` provide a simple command-line interface to manage `console_scripts` entry points in setup.py:

    projector console-scripts list
    projector console-scripts add <script-name> <entry-point> [--commit-changes]
    projector console-scripts remove <script-name> [--commit-changes]


### Adding package data

If you wish to include additional (non-Python-source) files in your python package distribution, `projector` can help you set it up:

    projector package-data list
    projector package-data add <filename> [--commit-changes]
    projector package-data remove <filename> [--commit-changes]

### Releasing versions

As we mentioned earlier, we use gitflow's branching model and versioning scheme. However, there's a little for to in releasing versions than just running one `git-flow` command:

* You need to find out the latest version number, and advance on top of it
* You need to bump the version-related files in the source
* You need to upload the version to PyPI
* You need to push the commit and tags to origin

`projector` solves all of these problems with the following command-line options:

    projector version release <version> [--no-fetch] (--no-upload | [--distributions=DISTRIBUTIONS] [--pypi-servers=PYPI_SERVERS]) [--push-changes]
    projector version upload <version> [--distributions=DISTRIBUTIONS] [--pypi-servers=PYPI_SERVERS]

Where the options are:

* `release`. Release a new version, including registering and uploading to pypi
* `upload`. Upload an existing version to pypi
* `--distributions=DISTRIBUTIONS`. Distributions to build [default: sdist,bdist_egg]
* `--pypi-servers=PYPI`. PyPI server for publishing [default: pypi,]
* `<version>`. x.y.z or major, minor, trivial (release only) or current, latest (upload only)
* `--no-upload`. Do not upload the package as part of the release process
* `--no-fetch`. Do not fetch origin before releasing
* `--push-changes`. We often forget to push the commits and tags to origin. This option does it for you

### Packaging applications (not just modules)

If you're developing a complete application, and not just a python package, you probably want to generate a sysadmin-friendly package of your app, bundled with its own iterpreter.

First, you'll need to build the development environment with the isolated python included:

    projector devenv build --isolated-python


Then, you can use `projector` can build stand-alone, isolated, packages. just run:

    projector devenv pack

Based on the platform you're running on, this command will generate a package under the `parts` directory:

* MSI on Windows platform, arhicture matches the OS (x86 for 32bit, x64 for 64bit)
* DEB on ubuntu
* RPM on redhat/centos

### Project/User defaults

In some cases, you'd want to always use a set of command-line arguments for a specific project, or maybe some user will want to use the same arguments for all their projects.
You can do so by writing the following configuration file to `./.projector` (per-project) or `~/.projector` (per-user):

    [commandline-arguments]
    --use-isolated-python = True
    --pypi-servers=pypi,local

This is just an example of course.

Developing projector
====================

Checking out the code
---------------------

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


