from sys import argv

#pylint: disable=R0801

def projector(argv=argv[1:]):
    from logging import basicConfig, INFO
    from infi.projector.commandline_parser import parse_commandline_arguments
    basicConfig(level=INFO)
    parse_commandline_arguments(argv)