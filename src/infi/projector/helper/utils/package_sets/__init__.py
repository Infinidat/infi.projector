from infi.projector.helper import assertions
from infi.projector.helper.utils import open_buildout_configfile

#pylint: disable=R0923

class PackageSetInterface(object): # pragma: no cover
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

    def from_value(self, value): # pragma: no cover
        raise NotImplementedError()

    def to_value(self, package_set): # pragma: no cover
        raise NotImplementedError()

class RepresentedListSet(BasePackageSet):
    def from_value(self, value):
        return set(eval(value))

    def to_value(self, package_set):
        return repr(list(set(package_set)))

class MultilineValueSet(BasePackageSet):
    def from_value(self, value):
        return set(value.splitlines())

    def to_value(self, package_set):
        newline = '\r\n' if assertions.is_windows() else '\n'
        return newline.join(list(set(package_set)))

class EntryPointSet(BasePackageSet):
    def from_value(self, value):
        formatted_entrypoints = eval(value)
        return {name.strip():entry_point.strip()
                for name, entry_point in [item.split('=') for item in formatted_entrypoints]}

    def to_value(self, package_set):
        return ["{} = {}".format(key, value) for key, value in package_set.items()]

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
                        if buildout.has_option(section, "recipe") and \
                        buildout.get(section, "recipe") == "infi.recipe.console_scripts"]
            return sections[0]

class ConsoleScriptsSet(EntryPointSet):
    def __init__(self):
        super(ConsoleScriptsSet, self).__init__('project', 'console_scripts')

class PackageDataSet(RepresentedListSet):
    def __init__(self):
        super(PackageDataSet, self).__init__('project', 'package_data')
