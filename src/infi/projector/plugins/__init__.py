from logging import getLogger

logger = getLogger(__name__)

COMMAND_PLUGIN_ENTRY_POINT = "projector_command_plugins"

class CommandPlugin(object):  # pragma: no cover
    def get_docopt_string(self):
        raise NotImplementedError()

    def get_command_name(self):
        raise NotImplementedError()

    def get_methods(self):
        raise NotImplementedError()

    def pre_command_assertions(self):
        pass

    def parse_commandline_arguments(self, arguments):
        methods = self.get_methods()
        matching_methods = [method for method in methods if arguments.get(method.__name__.replace('_', '-'))]
        self.arguments = arguments
        if matching_methods:
            method = matching_methods[0]
            self.pre_command_assertions()
            method()
            return True
        return False

class PluginRepository(object):
    def get_all_plugins(self):
        return [plugin_class() for plugin_class in self.get_all_plugin_classes()
                if self.validate_plugin(plugin_class)]

    def validate_plugin(self, plugin_class):
        if not issubclass(plugin_class, CommandPlugin):
            logger.error("Plugin {} is not a subclasss of CommandPlugin".format(plugin_class.__name__))
            return False
        methods = ["get_docopt_string", "get_command_name", "get_methods"]
        for method in [method for method in methods
                       if getattr(plugin_class, method) == getattr(CommandPlugin, method)]:
            logger.error("Plugin {} does not override {} ".format(plugin_class.__name__, method))
            return False
        return True

    def _iter_plugin_entry_points(self):
        from pkg_resources import iter_entry_points
        for entry_point in iter_entry_points(COMMAND_PLUGIN_ENTRY_POINT):
            try:
                yield entry_point.load()
            except Exception:
                logger.error("There was a problem loading plugin from entry point {!r}".format(entry_point))

    def get_plugin_clases_from_entry_points(self):
        return list(self._iter_plugin_entry_points())

    def get_all_plugin_classes(self):
        return self.get_plugin_clases_from_entry_points()

plugin_repository = PluginRepository()
