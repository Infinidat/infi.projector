
def get_all():
    from .repository import RepositoryPlugin
    from .build import BuildPlugin
    from .version import VersionPlugin
    return [RepositoryPlugin, BuildPlugin, VersionPlugin]