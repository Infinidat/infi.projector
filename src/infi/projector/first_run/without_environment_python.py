import sys
from os import makedirs, system, path, name

USE_ISOLATED_PYTHON = '--use-isolated-python' in sys.argv
IN_VIRTUALENV = hasattr(sys, 'real_prefix')
BUILDOUT = path.join("bin", "buildout")
COMMANDS = [
            "python {0} bootstrap.py -d -v 1.6.3".format('' if IN_VIRTUALENV else '-S'),
            "{0} -s buildout:develop= install setup.py __version__.py".format(BUILDOUT),
            "{0} -s install development-scripts".format(BUILDOUT)
           ]
if USE_ISOLATED_PYTHON:
    COMMANDS.insert(2, "{0} bootstrap.py -d -v 1.6.3".format(path.join("parts", "python", "bin",
                                                             "python{0}".format('.exe' if name == 'nt' else ''))))
    COMMANDS.insert(2, "{0} -s install isolated-python".format(BUILDOUT))

CACHE_DIST = path.join(".cache", "dist")
if not path.exists(CACHE_DIST):
    makedirs(path.join(".cache", "dist"))

for command in COMMANDS:
    print command
    if system(command):
        raise SystemExit(1)

