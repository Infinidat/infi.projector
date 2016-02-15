from infi.projector.helper import assertions
from infi.projector.helper.utils import open_buildout_configfile

def to_dict(iterable):
    from pkg_resources import parse_requirements
    return {item.project_name: item.specs for item in parse_requirements('\n'.join(iterable))}

def specs_to_string(value):
    return ''.join(value[0]) if value else ''

def from_dict(dict_object):
    return set(['{}{}'.format(key, specs_to_string(value)) for key, value in dict_object.items()])

class PackageSetInterface(object):  # pragma: no cover
    def get(self):
        raise NotImplementedError()

    def set(self, package_set):
        raise NotImplementedError()

class BasePackageSet(PackageSetInterface, object):
    def __init__(self, section_name, attribute_name):
        super(BasePackageSet, self).__init__()
        self.attribute_name = attribute_name
        self.section_name = section_name

    def get(self):
        with open_buildout_configfile() as buildout_cfg:
            return self.from_value(buildout_cfg.get(self.section_name, self.attribute_name))

    def set(self, package_set):
        with open_buildout_configfile(write_on_exit=True) as buildout_cfg:
            buildout_cfg.set(self.section_name, self.attribute_name, self.to_value(package_set))

    @classmethod
    def from_value(cls, value):  # pragma: no cover
        raise NotImplementedError()

    @classmethod
    def to_value(cls, package_set):  # pragma: no cover
        raise NotImplementedError()

class RepresentedListSet(BasePackageSet):
    @classmethod
    def from_value(cls, value):
        return set([item.replace(' ', '') for item in set(eval(value))])

    @classmethod
    def to_value(cls, package_set):
        items = [repr(item.replace(' ', '')) for item in set(package_set)]
        items.sort(key=lambda s: s.lower())
        newline = ',\r\n' if assertions.is_windows() else ',\n'
        return '[\n' + newline.join(items) + '\n]'

class MultilineValueSet(BasePackageSet):
    @classmethod
    def from_value(cls, value):
        return set(value.splitlines())

    @classmethod
    def to_value(cls, package_set):
        newline = '\r\n' if assertions.is_windows() else '\n'
        return newline.join(list(set(package_set)))

class EntryPointSet(BasePackageSet):
    @classmethod
    def from_value(cls, value):
        formatted_entrypoints = eval(value)
        return {name.strip(): entry_point.strip()
                for name, entry_point in [item.split('=') for item in formatted_entrypoints]}

    @classmethod
    def to_value(cls, package_set):
        items = ["'{} = {}'".format(key, value) for key, value in package_set.items()]
        items.sort(key=lambda s: s.lower())
        newline = ',\r\n' if assertions.is_windows() else ',\n'
        return '[\n' + newline.join(items) + '\n]'


class InstallRequiresPackageSet(RepresentedListSet):
    def __init__(self):
        super(InstallRequiresPackageSet, self).__init__('project', 'install_requires')

class EggsPackageSet(MultilineValueSet):
    def __init__(self):
        super(EggsPackageSet, self).__init__(self.get_section(), "eggs")

    @classmethod
    def get_section(cls):
        with open_buildout_configfile() as buildout:
            sections = [section for section in buildout.sections()
                        if buildout.has_option(section, "recipe") and
                        buildout.get(section, "recipe") == "infi.recipe.console_scripts"]
            return sections[0]

class ConsoleScriptsSet(EntryPointSet):
    def __init__(self):
        super(ConsoleScriptsSet, self).__init__('project', 'console_scripts')

class GuiScriptsSet(EntryPointSet):
    def __init__(self):
        super(GuiScriptsSet, self).__init__('project', 'gui_scripts')

class PackageDataSet(RepresentedListSet):
    def __init__(self):
        super(PackageDataSet, self).__init__('project', 'package_data')

class VersionSectionSet(PackageSetInterface, object):
    def __init__(self, filepath="versions.cfg", section_name="versions"):
        super(VersionSectionSet, self).__init__()
        self.filepath = filepath
        self.section_name = section_name

    def get(self):
        with open_buildout_configfile(self.filepath) as cfg:
            return self.from_value(cfg)

    def set(self, package_set):
        raise NotImplementedError()

    @classmethod
    def from_value(cls, cfg):  # pragma: no cover
        names = set()
        items = set()
        for option in cfg.options("versions"):
            if option in names:
                continue
            items.add("{}=={}".format(option, cfg.get("versions", option)))
        return items

    @classmethod
    def to_value(cls, package_set):  # pragma: no cover
        raise NotImplementedError()
