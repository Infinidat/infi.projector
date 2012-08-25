from textwrap import dedent

def parse_docopt_string(docopt_string):
    """returns a 2-tuple (usage, options)"""
    from re import match, DOTALL
    only_usage_pattern = r"""\s+Usage:\s+(?P<usage>.*)\s+"""
    usage_and_options_pattern = r"""\s+Usage:\s+(?P<usage>.*)\s+Options:\s+(?P<options>.*)\s+"""
    usage, options = '', ''
    if match(usage_and_options_pattern, docopt_string, DOTALL):
        usage = match(usage_and_options_pattern, docopt_string, DOTALL).groupdict()['usage']
        options = match(usage_and_options_pattern, docopt_string, DOTALL).groupdict()['options']
    elif match(only_usage_pattern, docopt_string, DOTALL):
        usage = match(only_usage_pattern, docopt_string, DOTALL).groupdict()['usage']
    return usage, options

def build_usage_and_options():
    from infi.projector.plugins import plugin_repository
    usage = ''
    options = ''
    for plugin in plugin_repository.get_all_plugins():
        docopt_string = plugin.get_docopt_string()
        plugin_usage, plugin_options = parse_docopt_string(docopt_string)
        usage = '\n'.join([usage, plugin_usage])
        options = '\n'.join([options, plugin_options])
    return usage, options

DEFAULT_USAGE = dedent("-h | --help\n-v | --version")
DEFAULT_OPTIONS = dedent("""-h            Show this screen.
                          -v            Show version.""")
SCRIPT_NAME = "projector"

def indent_usage(string):
    lines = [line.strip() for line in string.splitlines() if line.strip() != '']
    return '\n'.join(['    {}'.format(line if line.startswith(SCRIPT_NAME) else "{} {}".format(SCRIPT_NAME, line))
                      for line in lines])

def ident_options(string):
    lines = [line.strip() for line in string.splitlines() if line.strip() != '']
    options_tuple = [(item[0].strip(), item[1].strip()) for item in [line.split('  ', 1) for line in lines]]
    max_option_length = max([len(option_tuple[0]) for option_tuple in options_tuple]) + 4
    return '\n'.join(['    {}{}'.format(option_tuple[0].ljust(max_option_length), option_tuple[1])
                      for option_tuple in options_tuple])

def get_version():
    try:
        from infi.projector.__version__ import __version__
        return __version__
    except ImportError: # pragma: no cover
        return '<unknown>'

def get_commandline_doc():
    __version__ = get_version()
    usage, options = build_usage_and_options()
    doc = "{script_name} {version}\n\nUsage:\n{usage}\n\nOptions:\n{options}\n"
    all_usage = '\n'.join([usage, DEFAULT_USAGE])
    all_options = '\n'.join([DEFAULT_OPTIONS, options])
    return doc.format(script_name=SCRIPT_NAME,
                      usage=indent_usage(all_usage),
                      options=ident_options(all_options),
                      version=__version__)

def parse_commandline_arguments(argv):
    from infi.projector.plugins import plugin_repository
    from docopt import docopt
    doc = get_commandline_doc()
    arguments = docopt(doc, argv=argv, version=get_version())
    if arguments.get('-v'):
        print get_version()
        return
    plugins = {plugin.get_command_name():plugin for plugin in plugin_repository.get_all_plugins()}
    [selected_plugin] = [value for key, value in plugins.items() if arguments.get(key)]
    selected_plugin.parse_commandline_arguments(arguments)
