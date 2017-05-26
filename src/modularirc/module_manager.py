import pkgutil
import os
import sys
from imp import reload
import logging
import importlib

from modularirc.modules import loader

def get_modules():
    """Returns all modules that are found in the current package.
    Excludes modules starting with '_'"""
    return [module_info.name for module_info in loader.list_modules()]

def get_module(name):
    """Import module <module> and return the class.
    This returns the class object"""
    module_info = {module_info.name: module_info for module_info in loader.list_modules()}[name]
    return loader.load_module(module_info).Module

def reload_module(module):
    """Reload a module given the module name.
    This should be just the name, not the full module path.

    Arguments:
    module: the name of the module

    Returns:
    success, bool
    """

    try:
        reload(getattr(sys.modules[__name__], module))
        return True
    except AttributeError:
        return False

class ModuleManager(object):
    def __init__(self, bot, blacklist=None):
        self.bot = bot
        self.modules = {}
        self.loaded_modules = {}
        blacklist = blacklist or []
        for module_name in get_modules():
            if module_name in blacklist:
                continue
            logging.info('Loading module {0}: {1}'.format(module_name, self.add_module(module_name)))

    def unload(self):
        for module_name in list(self.modules.keys()):
            logging.info('Unloading module {0}: {1}'.format(module_name, self.remove_module(module_name)))

    def reload_modules(self):
        """Reload all modules. Warning: this is fairly destructive"""
        # remove modules that no longer exist
        for module_name in [m for m in self.modules.keys() if m not in get_modules()]:
            self.remove_module(module_name)
        # reload all modules
        for module_name in self.modules:
            self.reload_module(module_name)
        # add modules that are not added yet
        for module_name in [m for m in get_modules() if m not in self.modules]:
            self.add_module(module_name)

    def get_modules(self):
        """Get all found modules"""
        return self.modules.keys()

    def get_loaded_modules(self):
        return self.get_enabled_modules()

    def get_enabled_modules(self):
        """Get all enabled modules"""
        return self.loaded_modules.items()

    def module_is_loaded(self, module_name):
        return module_name in self.loaded_modules

    def get_module(self, module_name):
        try:
            return self.loaded_modules[module_name]
        except:
            return False

    def get_available_modules(self):
        """Get all available modules: modules that are found but not loaded"""
        modules = [key for key in self.modules.keys() if key not in self.loaded_modules]
        modules.sort()
        return modules

    def add_module(self, module_name):
        """Load a module"""
        if module_name in self.modules:
            return 'Module already available'
        try:
            module = get_module(module_name)
            if module:
                self.modules[module_name] = module
                return 'Module added'
        except AttributeError as e: #Exception as e:
            return 'Error loading module: {0}'.format(e)
        return 'Module not available'

    def remove_module(self, module_name):
        """Unload a module"""
        if module_name not in self.modules:
            return 'Module not available'
        if module_name in self.loaded_modules:
            self.disable_module(module_name)
        del self.modules[module_name]
        return 'Module removed'

    def enable_module(self, module_name):
        """Enable a module"""
        if module_name not in self.modules:
            return 'Module {} not available'.format(module_name)
        if module_name in self.loaded_modules:
            return 'Module {} already enabled'.format(module_name)
        try:
            self.loaded_modules[module_name] = self.modules[module_name](self)
        except Exception as e:
            # raise ModuleLoadException(e)
            return 'Module {} failed to load: {}'.format(module_name, e)
        return 'Module {} enabled'.format(module_name)

    def disable_module(self, module_name):
        """Disable a module"""
        if module_name not in self.loaded_modules:
            return 'Module not enabled'
        try:
            self.loaded_modules[module_name].stop()
        except Exception as e:
            logger.warning('Module %s failed to stop: %s', module_name, e)
        del self.loaded_modules[module_name]
        return 'Module {} disabled'.format(module_name)

    def restart_module(self, module_name):
        """Restart a module"""
        if module_name not in self.modules:
            return 'Module {} not available'.format(module_name)
        if module_name in self.loaded_modules:
            self.disable_module(module_name)
        self.enable_module(module_name)
        return 'Module {} restarted'.format(module_name)

    def reload_module(self, module_name):
        """Reload a module"""
        start_module = module_name in self.loaded_modules
        self.remove_module(module_name)  # remove to clear references
        reload_module(module_name)  # actually reload class
        self.add_module(module_name)  # re-add module
        if start_module:  # enable if it was enabled
            self.enable_module(module_name)
        return 'Module {} reloaded'.format(module_name)

    def get_module(self, name):
        if name in self.loaded_modules:
            return self.loaded_modules[name]

    # methods from Bot
    def __getattr__(self, key):
        if key in ('notice', 'privmsg', 'get_config', 'set_config'):
            return getattr(self.bot, key)
