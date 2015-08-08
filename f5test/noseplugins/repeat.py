'''
Created on Feb 20, 2014

@author: jono
'''
from __future__ import absolute_import
from nose.plugins.base import Plugin
from nose.case import Test
import logging
import datetime

LOG = logging.getLogger(__name__)
STDOUT = logging.getLogger('stdout')
PLUGIN_NAME = 'repeat'
ATTR = '_repeat'


def repeat(times=None, seconds=None):
    def _my_decorator(f):
        setattr(f, ATTR, dict(times=times, seconds=seconds))
        return f
    return _my_decorator


class Repeat(Plugin):
    """
    Repeat a test plugin. Enabled by default.
    """
    enabled = True
    name = "repeat"
    score = 520

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--no-repeat', action='store_true',
                          dest='no_repeat', default=False,
                          help="Disable Repeat plugin. (default: no)")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        Plugin.configure(self, options, noseconfig)
        self.options = options
        if not options.no_repeat:
            # Monkey patch Test.__call__ to handle @repeat decorated tests.
            def __call__(self, result, blocking_context=None):
                testMethod = getattr(self.test, self.test._testMethodName)
                attrs = getattr(testMethod, ATTR, {})
                if not any(attrs.values()):
                    return self.run(result, blocking_context)

                times = attrs.get('times') or -1
                end = datetime.datetime.now() + datetime.timedelta(seconds=attrs.get('seconds') or -1)
                ret = i = 0
                while i < times or datetime.datetime.now() < end:
                    ret = self.run(result, blocking_context)
                    i += 1
                    if blocking_context:
                        break
                return ret
            Test.__call__ = __call__
