'''
Created on Jun 23, 2011

@author: jono
'''
from __future__ import absolute_import
from nose.plugins.base import Plugin
import logging
import datetime
import nose.util
import time
from ..utils.time import timesince

LOG = logging.getLogger(__name__)
PLUGIN_NAME = 'testtime'


def test_address(test):
    """Return the result of nose's test_address(), None if it's stumped."""
    try:
        return nose.util.test_address(test)
    except TypeError:   # Explodes if the function passed to @with_setup applied
                        # to a test generator has an error.
        pass


def nose_selector(test):
    """Return the string you can pass to nose to run `test`, including argument
    values if the test was made by a test generator.

    Return "Unknown test" if it can't construct a decent path.

    """
    address = test_address(test)
    if address:
        _, module, rest = address

        if module:
            if rest:
                try:
                    return '%s:%s%s' % (module, rest, test.test.arg or '')
                except AttributeError:
                    return '%s:%s' % (module, rest)
            else:
                return module
    return 'Unknown test'


class TestTime(Plugin):
    """
    Test time plugin. Enabled by default. Disable with ``--no-testtime``. This
    plugin captures tracks the time taken to execute each test and the entire
    test suite.
    """
    enabled = True
    name = "testtime"
    score = 520

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--no-testtime', action='store_true',
                          dest='no_testtime', default=False,
                          help="Disable TestTime reporting. (default: no)")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        from ..interfaces.config import ConfigInterface
        from ..interfaces.testcase import ContextHelper
        self.cfgifc = ConfigInterface()
        self.context = ContextHelper('__main__')

        Plugin.configure(self, options, noseconfig)
        self.options = options
        if options.no_testtime:
            self.enabled = False

    def prepareTestResult(self, result):
        result.descriptions = 0
        result.getDescription = lambda y: nose_selector(y)

    def startTest(self, test):
        """Initializes a timer before starting a test."""
        self.start = time.time()
        adr = test.id()
        LOG.info('* Run * %s', adr)

    def stopTest(self, test):
        """Initializes a timer before starting a test."""
        now = time.time()
        #_, module, method = test.address()
        #adr = "%s:%s" % (module, method)
        adr = test.id()
        LOG.info('* Time * %s: %.3fs', adr, now - self.start)

    def begin(self):
        """Set the testrun start time.
        """
        container = self.context.set_container(PLUGIN_NAME)
        container.start = datetime.datetime.now()

    def finalize(self, result):
        """Set the testrun stop time and delta.
        """
        container = self.context.set_container(PLUGIN_NAME)
        container.stop = datetime.datetime.now()
        container.delta = container.stop - container.start
        container.delta_str = timesince(container.start)
