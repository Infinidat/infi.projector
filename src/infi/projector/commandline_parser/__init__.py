from __future__ import print_function
from textwrap import dedent
from logging import getLogger
from infi.projector.helper.utils import configparser

logger = getLogger(__name__)

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

def sort_options(options):
    def key_cmp(key):
        key = key.strip()
        if key.startswith("<"):
            return 1
        if key.startswith("-"):
            return 2
        return 0
    return '\n'.join(sorted(options.split("\n"), key=key_cmp))

def build_usage_and_options():
    from infi.projector.plugins import plugin_repository
    usage = ''
    options = ''
    for plugin in sorted(plugin_repository.get_all_plugins(), key=lambda plugin: plugin.get_command_name()):
        docopt_string = plugin.get_docopt_string()
        plugin_usage, plugin_options = parse_docopt_string(docopt_string)
        usage = '\n'.join([usage, plugin_usage])
        options = '\n'.join([options, plugin_options])
    options = sort_options(options)
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
    except ImportError:  # pragma: no cover
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

def parse_configfile(configfile_path):
    parser = configparser.ConfigParser()
    parser.read(configfile_path)
    return parser

def parse_configfile_value(value):
    try:
        return eval(value)
    except:
        return value

def merge_commandline_arguments_from_configfile(arguments, configfile_path):
    try:
        configuration = parse_configfile(configfile_path)
        logger.debug("Failed to parse {}".format(configfile_path))
    except confirparser.Error:
        return
    if not configuration.has_section("commandline-arguments"):
        logger.debug("File {} has no commandline-arguments".format(configfile_path))
        return
    for name, value in configuration.items("commandline-arguments"):
        if arguments.get('name') in [None, False, list()]:
            logger.debug("Setting commandline-argument {} to {}".format(name, value))
            arguments[name] = parse_configfile_value(value)

def append_default_arguments_from_configuration_files(arguments):
    from os import curdir, path
    CONFIGURATION_FILES = [path.expanduser(path.join("~", ".projector")),
                           path.join(curdir, ".projector")]
    for configfile_path in CONFIGURATION_FILES:
        merge_commandline_arguments_from_configfile(arguments, configfile_path)

def parse_commandline_arguments(argv):
    from infi.projector.plugins import plugin_repository
    from docopt import docopt
    doc = get_commandline_doc()
    arguments = dict(docopt(doc, argv=argv, version=get_version()))
    if arguments.get('-v'):
        print(get_version())
        return
    selected_plugins = [plugin for plugin in plugin_repository.get_all_plugins()
                        if arguments.get(plugin.get_command_name())]
    append_default_arguments_from_configuration_files(arguments)
    if not selected_plugins:
        logger.error("No matching plugin found")
        return
    if not any(selected_plugin.parse_commandline_arguments(arguments) for selected_plugin in selected_plugins):
        logger.error("No matching method found")
        return

