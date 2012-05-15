from nose.plugins.base import Plugin
from nose.util import tolist
from ..base import AttrDict
import ast
import os
import logging

log = logging.getLogger(__name__)
config = None

def merge(user, default):
    if isinstance(user, dict) and isinstance(default,dict):
        for k,v in default.iteritems():
            if k not in user:
                user[k] = v
            else:
                user[k] = merge(user[k],v)
    return user

def extend(cwd, config, loader):
    if isinstance(config.get('$extends'), list):
        for filename in config.get('$extends'):
            filename = os.path.join(cwd, filename)
            base_config = extend(cwd, loader(filename), loader)
            config = merge(config, base_config)
    elif isinstance(config.get('$extends'), str):
        filename = os.path.join(cwd, config.get('$extends'))
        base_config = loader(filename)
        config = merge(config, base_config)
    return config

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

    enabled = False
    name = "test_config"
    # High score means further head in line.
    score = 550

    env_opt = "NOSE_TEST_CONFIG_FILE"
    format = "ini" #@ReservedAssignment
    valid_loaders = { 'yaml' : load_yaml, 'ini' : load_ini,
                      'python' : load_python }

    def __init__(self, override_config=None):
        Plugin.__init__(self)
        self.override_config = False
        if override_config:
            global config
            config = override_config
            self.override_config = True

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
            default=env.get('NOSE_TEST_CONFIG_FILE_FORMAT') or self.format, 
            dest="testconfigformat",
            help="Test config file format, default is configparser ini format"
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
        Plugin.configure(self, options, noseconfig)

        self.config = noseconfig
        if not options.capture:
            self.enabled = False
        if options.testconfigformat:
            self.format = options.testconfigformat
            if self.format not in self.valid_loaders.keys():
                raise Exception('%s is not a valid configuration file format' \
                                                                % self.format)

        # Load the configuration file:
        global config
        filename = os.path.expandvars(options.testconfig)
        if not self.override_config:
            config = self.valid_loaders[self.format](filename)
        
        cwd = os.path.dirname(filename)
        config = extend(cwd, config, self.valid_loaders[self.format])
        
        if options.overrides:
            self.overrides = []
            overrides = tolist(options.overrides)
            for override in overrides:
                keys, val = override.split(":")
                # Attempt to convert the string into int/bool/float or default
                # to string
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
        
        config = AttrDict(config)
        config['_filename'] = filename

# Use an environment hack to allow people to set a config file to auto-load
# in case they want to put tests they write through pychecker or any other
# syntax thing which does an execute on the file.
if config is None:
    if 'NOSE_TESTCONFIG_AUTOLOAD_YAML' in os.environ:
        filename = os.path.expandvars(os.environ['NOSE_TESTCONFIG_AUTOLOAD_YAML'])
        tmp = load_yaml(filename)
        cwd = os.path.dirname(filename)
        config = extend(cwd, tmp, load_yaml)
        config = AttrDict(config)
    
    if 'NOSE_TESTCONFIG_AUTOLOAD_INI' in os.environ:
        filename = os.path.expandvars(os.environ['NOSE_TESTCONFIG_AUTOLOAD_INI'])
        tmp = load_ini(filename)
        cwd = os.path.dirname(filename)
        config = extend(cwd, tmp, load_ini)
        config = AttrDict(config)
    
    if 'NOSE_TESTCONFIG_AUTOLOAD_PYTHON' in os.environ:
        filename = os.path.expandvars(os.environ['NOSE_TESTCONFIG_AUTOLOAD_PYTHON'])
        tmp = load_python(filename)
        cwd = os.path.dirname(filename)
        config = extend(cwd, tmp, load_python)
        config = AttrDict(config)
