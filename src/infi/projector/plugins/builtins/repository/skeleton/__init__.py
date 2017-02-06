
FILENAMES = [".gitignore", "README.md", "get-pip.py", "buildout.cfg", "setup.in"]
FILENAMES_TO_UPDATE = ["bootstrap.py", "buildout.cfg", "setup.in"]

def get_files():
    from pkg_resources import resource_filename
    return [resource_filename(__name__, filename) for filename in FILENAMES]

def get_files_to_update():
    from pkg_resources import resource_filename
    return [resource_filename(__name__, filename) for filename in FILENAMES_TO_UPDATE]
