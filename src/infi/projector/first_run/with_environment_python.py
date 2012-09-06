#!/usr/bin/env python

PACKAGE_QUICKS = {
                  'distribute': 'setuptools',
                  'git-py': 'gitpy'
                  }

def append_src_to_python_path():
    import sys
    sys.path.append('src')

def get_dependencies():
    from infi.projector.helper.utils import open_buildout_configfile
    with open_buildout_configfile() as buildout:
        exec 'dependencies = {}'.format(buildout.get("project", "install_requires"))
    return dependencies

def is_dependency_installed(dependency):
    separators = ['>', '<', '=']
    module_name = dependency
    for sep in separators:
        if sep in dependency:
            module_name = dependency.split(sep)[0]
            break
    try:
        __import__(PACKAGE_QUICKS.get(module_name, module_name))
    except ImportError:
        return False
    return True

def check_for_dependencies():
    missing_dependencies = [dependency for dependency in get_dependencies()
                            if not is_dependency_installed(dependency)]
    if missing_dependencies:
        print 'Please install the following dependencies: {}'.format(' '.join(missing_dependencies))
        raise SystemExit(1)

def build_scripts():
    import sys
    from infi.projector.scripts import projector
    projector(' '.join(['build', 'scripts'] + sys.argv[1:]))

def main():
    append_src_to_python_path()
    check_for_dependencies()
    build_scripts()

if __name__ == '__main__':
    main()

