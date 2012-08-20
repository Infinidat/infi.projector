
FILENAMES = [".gitignore", "README.md", "bootstrap.py", "buildout.cfg", "buildout.in", "setup.in"]

def get_files():
    from pkg_resources import resource_filename
    return [resource_filename(__name__, filename) for filename in FILENAMES]