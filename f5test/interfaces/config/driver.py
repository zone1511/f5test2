'''
Created on Mar 16, 2013

@author: jono
'''
from ...base import AttrDict
from ...utils.dicts import merge
from ...utils.net import get_local_ip
from blinker import Signal
import os
import logging
import sys
import threading

LOG = logging.getLogger(__name__)
CONFIG = threading.local()
EXTENDS_KEYWORD = '$extends'
PEER_IP = '224.0.0.1'


class Signals(object):
    on_before_load = Signal()
    on_before_extend = Signal()
    on_after_extend = Signal()


class ConfigLoader(object):

    def __init__(self, filename, fmt=None):
        self.loaders = {'yaml': self.load_yaml,
                        'json': self.load_json,
                        'ini': self.load_ini,
                        'py': self.load_python}
        self.filename = filename
        self.fmt = fmt

    def load(self):
        # Load the configuration file:
        Signals.on_before_load.send(self, filename=self.filename)
        main_config = self.load_any(self.filename)

        config_dir = os.path.dirname(self.filename)
        Signals.on_before_extend.send(self, config=main_config)
        config = self.extend(config_dir, main_config)

        config = AttrDict(config)
        config['_filename'] = self.filename
        config['_argv'] = ' '.join(sys.argv)
        config['_cwd'] = os.getcwd()
        config['_local_ip'] = get_local_ip(PEER_IP)

        Signals.on_after_extend.send(self, config=config)
        return config

    def extend(self, cwd, config, extra=None):
        bases = config.get(EXTENDS_KEYWORD) or []
        if bases and isinstance(bases, basestring):
            bases = [bases]

        if extra and isinstance(extra, basestring):
            extra = [extra]
        else:
            extra = []

        assert isinstance(bases, list), 'Expected a list of files in %s' % EXTENDS_KEYWORD
        bases += extra

        for filename in reversed(bases):
            filename = os.path.join(cwd, filename)
            base_config = self.extend(os.path.dirname(filename),
                                      self.load_any(filename))
            # Substitute {0[..]} tokens. Works only with strings.
            self.subst_variables(config, base_config)
            config = merge(base_config, config)
        return config

    def subst_variables(self, src, root=None):
        if not root:
            root = src

        def _subst(hashable, key):
            try:
                if isinstance(hashable[key], basestring):
                    hashable[key] = hashable[key].format(CFG=root, ENV=os.environ)
            except (KeyError, ValueError):
                LOG.debug('Key %s cannot be formatted.', v)

        if isinstance(src, dict):
            for k, v in src.iteritems():
                if isinstance(v, dict):
                    self.subst_variables(v, root)
                elif isinstance(v, basestring):
                    _subst(src, k)
                elif isinstance(v, (list, tuple)):
                    for i in range(len(v)):
                        if isinstance(v[i], dict):
                            self.subst_variables(v[i], root)
                        else:
                            _subst(v, i)

    def load_any(self, filename):
        fmt = self.fmt or os.path.splitext(filename)[1][1:]
        assert fmt in self.loaders, 'Unknown format: %s' % fmt
        return self.loaders[fmt](filename)

    @staticmethod
    def load_yaml(filename):
        """ Load the passed in yaml configuration file """
        try:
            import yaml
        except (ImportError):
            raise Exception('unable to import YAML package. Can not continue.')
        return yaml.load(open(filename).read())

    @staticmethod
    def load_ini(filename):
        """ Parse and collapse a ConfigParser-Style ini file into a nested,
        eval'ing the individual values, as they are assumed to be valid
        python statement formatted """
        import ConfigParser
        tmpconfig = ConfigParser.ConfigParser()
        tmpconfig.read(filename)
        config = {}
        for section in tmpconfig.sections():
            config[section] = {}
            for option in tmpconfig.options(section):
                config[section][option] = tmpconfig.get(section, option)
        return config

    @staticmethod
    def load_python(filename):
        """ This will eval the defined python file into the config variable -
        the implicit assumption is that the python is safe, well formed and will
        not do anything bad. This is also dangerous. """
        return eval(open(filename, 'r').read())

    @staticmethod
    def load_json(filename):
        import json
        return json.load(open(filename))
