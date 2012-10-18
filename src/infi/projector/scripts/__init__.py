from sys import argv
#pylint: disable=R0801

def projector(argv=argv[1:]):
    from os import environ
    from logging import basicConfig, INFO, DEBUG, getLogger
    from sys import stderr
    from infi.projector.commandline_parser import parse_commandline_arguments
    basicConfig(level=DEBUG if environ.get("DEBUG") else INFO, stream=stderr)
    getLogger(__name__).debug(' '.join(['projector'] + argv))
    parse_commandline_arguments(argv)
