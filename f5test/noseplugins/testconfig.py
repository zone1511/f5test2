from nose.plugins.base import Plugin
from nose.util import tolist
from ..interfaces.config import ConfigLoader, ConfigInterface
import ast
import os
#import logging

#LOG = logging.getLogger(__name__)


class TestConfig(Plugin):
    """
    Test Config plugin. Enabled by when ``--tc-file`` is passed. Parses a config
    file (usually in YAML format) and stores it in a global variable as a
    dictionary. Use ConfigInterface to read/write from/to this config
    variable.
    """
    enabled = False
    name = "test_config"
    # High score means further head in line.
    score = 550

    env_opt = "NOSE_TEST_CONFIG_FILE"

    def options(self, parser, env=os.environ):
        """ Define the command line options for the plugin. """
        parser.add_option(
            "--tc-file", action="store",
            default=env.get(self.env_opt),
            help="Configuration file to parse and pass to tests"
                 " [NOSE_TEST_CONFIG_FILE]")
        parser.add_option(
            "--tc-format", action="store",
            default=env.get('NOSE_TEST_CONFIG_FILE_FORMAT'),
            help="Test config file format, default is: autodetect"
                 " [NOSE_TEST_CONFIG_FILE_FORMAT]")
        parser.add_option(
            "--tc", action="append",
            dest="overrides",
            default=[],
            help="Option:Value specific overrides.")
        parser.add_option(
            "--tc-exact", action="store_true",
            default=False,
            help="Optional: Do not explode periods in override keys to "
                 "individual keys within the config dict, instead treat them"
                 " as config[my.toplevel.key] ala sqlalchemy.url in pylons")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        if not options.tc_file:
            return

        self.enabled = True
        Plugin.configure(self, options, noseconfig)
        loader = ConfigLoader(options.tc_file, options.tc_format)
        cfgifc = ConfigInterface(loader=loader)
        cfgifc.set_global_config()
        config = cfgifc.get_config()

        if options.overrides:
            self.overrides = []
            overrides = tolist(options.overrides)
            for override in overrides:
                keys, val = override.split(":")
                # Attempt to convert the string into int/bool/float or default
                # to string
                if val == '':
                    val = None
                else:
                    needquotes = False
                    try:
                        val = ast.literal_eval(val)
                    except ValueError:
                        needquotes = True

                    if needquotes or isinstance(val, basestring):
                        val = '"%s"' % val

                if options.tc_exact:
                    config[keys] = val
                else:
                    ns = ''.join(['["%s"]' % i for i in keys.split(".")])
                    # BUG: Breaks if the config value you're overriding is not
                    # defined in the configuration file already. TBD
                    exec('config%s = %s' % (ns, val))

    def begin(self):
        from ..interfaces.testcase import ContextHelper
        context = ContextHelper('__main__')
        context._clear()
        context.set_container()
