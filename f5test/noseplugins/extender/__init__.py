'''
Created on Jul 24, 2014

@author: jono
'''
import importlib
import inspect
import logging
import pkgutil

from nose.plugins.base import Plugin


LOG = logging.getLogger(__name__)
PLUGIN_NAME = 'reporting'


class ExtendedPlugin(Plugin):
    score = 500

    def options(self, parser, env):
        pass

    def configure(self, options, noseconfig):
        if options.enabled is not None:
            self.enabled = bool(options.enabled)
        if options.get('score'):
            self.score = int(options.score)
        self.options = options
        self.noseconfig = noseconfig


class Extender(Plugin):
    """
    Gather data about tests and store it in the "reporting" container.
    Enabled by default.
    """
    enabled = True
    name = "extender"
    score = 500

    def __init__(self):
        super(Extender, self).__init__()
        # parent = importlib.import_module(__name__.rsplit('.', 1)[0])
        self.plugins = []

        # Find and load all our plugins and attach them to nose
        # parent = importlib.import_module(__name__.rsplit('.', 1)[0])
        parent = importlib.import_module(__name__)
        for _, module_name, _ in pkgutil.walk_packages(parent.__path__):
            module = importlib.import_module('%s.%s' % (parent.__name__, module_name))
            for _, klass in inspect.getmembers(module, lambda x: inspect.isclass(x)):
                if issubclass(klass, ExtendedPlugin) and klass is not ExtendedPlugin:
                    plugin = klass()
                    self.plugins.append(plugin)

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--no-extender', action='store_true',
                          dest='no_extender', default=False,
                          help="Disable this plugin. (default: no)")

        for plugin in self.plugins:
            plugin.addOptions(parser, env)

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        from ...base import Options as O
        from ...interfaces.config import ConfigInterface

        self.options = options
        if options.no_extender:
            self.enabled = False

        with ConfigInterface() as cfgifc:
            plugin_options = cfgifc.api.plugins or O()

        for plugin in self.plugins:
            LOG.debug('Configuring plugin: %s', plugin.name)
            plugin.configure(plugin_options.get(plugin.name) or O(), noseconfig)
            noseconfig.plugins.addPlugin(plugin)

        noseconfig.plugins.sort()
