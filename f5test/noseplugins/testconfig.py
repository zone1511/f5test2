from nose.plugins.base import Plugin
from nose.util import tolist
from ..base import AttrDict
import ast
from blinker import Signal
import os
import logging
import threading

log = logging.getLogger(__name__)
CONFIG = threading.local()
#CONFIG = AttrDict()
EXTENDS_KEYWORD = '$extends'

class Signals(object):
    on_before_load = Signal()
    on_before_extend = Signal()
    on_after_extend = Signal()

def merge(dst, src):
    if isinstance(dst, dict) and isinstance(src,dict):
        for k,v in src.iteritems():
            if k.startswith('$'):
                continue
            if k not in dst:
                dst[k] = v
            else:
                dst[k] = merge(dst[k],v)
    else:
        return src
    return dst

def extend(cwd, config, loader):
    if isinstance(config.get(EXTENDS_KEYWORD), list):
        for filename in reversed(config.get(EXTENDS_KEYWORD)):
            filename = os.path.join(cwd, filename)
            base_config = extend(cwd, loader(filename), loader)
            config = merge(base_config, config)
    return config

def subst_variables(src, root=None):
    if not root:
        root = src
    
    if isinstance(src, dict):
        for k,v in src.iteritems():
            if isinstance(v, dict):
                subst_variables(v, root)
            elif isinstance(v, basestring):
                try:
                    src[k] = src[k].format(CFG=root, ENV=os.environ)
                except KeyError:
                    log.debug('Key %s cannot be formatted.', v)

def load_yaml(yaml_file):
    """ Load the passed in yaml configuration file """
    try:
        import yaml
    except (ImportError):
        raise Exception('unable to import YAML package. Can not continue.')
    return yaml.load(open(yaml_file).read())

def load_ini(ini_file):
    """ Parse and collapse a ConfigParser-Style ini file into a nested,
    eval'ing the individual values, as they are assumed to be valid
    python statement formatted """

    import ConfigParser
    tmpconfig = ConfigParser.ConfigParser()
    tmpconfig.read(ini_file)
    config = {}
    for section in tmpconfig.sections():
        config[section] = {}
        for option in tmpconfig.options(section):
            config[section][option] = tmpconfig.get(section, option)
    return config

def load_python(py_file):
    """ This will exec the defined python file into the config variable - 
    the implicit assumption is that the python is safe, well formed and will
    not do anything bad. This is also dangerous. """
    exec(open(py_file, 'r'))


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
    valid_loaders = { 'yaml' : load_yaml, 'yml' : load_yaml,
                      'ini' : load_ini,
                      'python' : load_python, 'py' : load_python }

    def options(self, parser, env=os.environ):
        """ Define the command line options for the plugin. """
        parser.add_option(
            "--tc-file", action="store",
            default=env.get(self.env_opt),
            dest="testconfig",
            help="Configuration file to parse and pass to tests"
                 " [NOSE_TEST_CONFIG_FILE]")
        parser.add_option(
            "--tc-format", action="store",
            default=env.get('NOSE_TEST_CONFIG_FILE_FORMAT'), 
            dest="testconfigformat",
            help="Test config file format, default is: autodetect"
                 " [NOSE_TEST_CONFIG_FILE_FORMAT]")
        parser.add_option(
            "--tc", action="append", 
            dest="overrides",
            default = [],
            help="Option:Value specific overrides.")
        parser.add_option(
            "--tc-exact", action="store_true", 
            dest="exact",
            default = False,
            help="Optional: Do not explode periods in override keys to "
                 "individual keys within the config dict, instead treat them"
                 " as config[my.toplevel.key] ala sqlalchemy.url in pylons")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        if not options.testconfig:
            return

        #if noseconfig.plugin_testconfig:
        #    CONFIG.data = noseconfig.plugin_testconfig

        self.enabled = True
        Plugin.configure(self, options, noseconfig)
        filename = os.path.expandvars(options.testconfig)
        self.config = noseconfig
        
        if options.testconfigformat:
            self.format = options.testconfigformat
            if self.format not in self.valid_loaders.keys():
                raise ValueError('%s is not a valid configuration file format' % self.format)
        else:
            self.format = os.path.splitext(filename)[1][1:]

        # Load the configuration file:
        Signals.on_before_load.send(self, filename=filename)
        main_config = self.valid_loaders[self.format](filename)
        
        cwd = os.path.dirname(filename)
        Signals.on_before_extend.send(self, config=main_config)
        config = extend(cwd, main_config, self.valid_loaders[self.format])
        
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

                if options.exact:
                    config[keys] = val
                else:                    
                    ns = ''.join(['["%s"]' % i for i in keys.split(".") ])
                    # BUG: Breaks if the config value you're overriding is not
                    # defined in the configuration file already. TBD
                    exec('config%s = %s' % (ns, val))
        
        # Substitute {0[..]} tokens.
        subst_variables(config)
        config = AttrDict(config)
        config['_filename'] = filename

        CONFIG.data = config
        Signals.on_after_extend.send(self, config=config)

# Use an environment hack to allow people to set a config file to auto-load
# in case they want to put tests they write through pychecker or any other
# syntax thing which does an execute on the file.
if getattr(CONFIG, 'data', None) is None:
    if 'NOSE_TESTCONFIG_AUTOLOAD_YAML' in os.environ:
        filename = os.path.expandvars(os.environ['NOSE_TESTCONFIG_AUTOLOAD_YAML'])
        tmp = load_yaml(filename)
        cwd = os.path.dirname(filename)
        config = extend(cwd, tmp, load_yaml)
        CONFIG.data = AttrDict(config)
    
    if 'NOSE_TESTCONFIG_AUTOLOAD_INI' in os.environ:
        filename = os.path.expandvars(os.environ['NOSE_TESTCONFIG_AUTOLOAD_INI'])
        tmp = load_ini(filename)
        cwd = os.path.dirname(filename)
        config = extend(cwd, tmp, load_ini)
        CONFIG.data = AttrDict(config)
    
    if 'NOSE_TESTCONFIG_AUTOLOAD_PYTHON' in os.environ:
        filename = os.path.expandvars(os.environ['NOSE_TESTCONFIG_AUTOLOAD_PYTHON'])
        tmp = load_python(filename)
        cwd = os.path.dirname(filename)
        config = extend(cwd, tmp, load_python)
        CONFIG.data = AttrDict(config)
