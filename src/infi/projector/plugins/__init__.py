from infi.pyutils.lazy import cached_method
from logging import getLogger

logger = getLogger(__name__)

class CommandPlugin(object):
    def get_docopt_string(self):
        raise NotImplementedError()

    def get_command_name(self):
        raise NotImplementedError()

    def parse_commandline_arguments(self, arguments):
        raise NotImplementedError()

class PluginRepository(object):
    @cached_method
    def get_all_plugins(self):
        return [plugin_class() for plugin_class in self.get_all_plugin_classes()
                if self.validate_plugin(plugin_class)]

    def validate_plugin(self, plugin_class):
        if not issubclass(plugin_class, CommandPlugin):
            logger.error("Plugin {} is not a subclasss of CommandPlugin".format(plugin_class.__name__))
            return False
        methods = ["get_docopt_string", "get_command_name", "parse_commandline_arguments"]
        for method in [method for method in methods
                       if getattr(plugin_class, method) == getattr(CommandPlugin, method)]:
            logger.error("Plugin {} does not override {} ".format(plugin_class.__name__, method))
            return False
        return True

    def get_builtin_plugins_classes(self):
        from .builtins import get_all
        return get_all()

    def get_external_plugin_classes(self):
        return []

    def get_all_plugin_classes(self):
        return self.get_builtin_plugins_classes() + self.get_external_plugin_classes()

plugin_repository = PluginRepository()
