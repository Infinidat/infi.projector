import sys
from os import makedirs, system, path, name

USE_ISOLATED_PYTHON = '--use-isolated-python' in sys.argv
IN_VIRTUALENV = hasattr(sys, 'real_prefix')
BUILDOUT = path.join("bin", "buildout")
COMMANDS = [
            "python {} bootstrap.py -d".format('' if IN_VIRTUALENV else '-S'),
            "{} -s buildout:develop= install setup.py __version__.py".format(BUILDOUT),
            "{} -s install development-scripts".format(BUILDOUT)
           ]
if USE_ISOLATED_PYTHON:
    COMMANDS.insert(2, "{} bootstrap.py -d".format(path.join("parts", "python", "bin",
                                                             "python{}".format('.exe' if name == 'nt' else ''))))
    COMMANDS.insert(2, "{} -s install isolated-python".format(BUILDOUT))

CACHE_DIST = path.join(".cache", "dist")
if not path.exists(CACHE_DIST):
    makedirs(path.join(".cache", "dist"))

for command in COMMANDS:
    print command
    if system(command):
        raise SystemExit(1)

