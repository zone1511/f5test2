'''
Created on Jun 23, 2011

@author: jono
'''
from __future__ import absolute_import
from nose.plugins.base import Plugin
import logging
import datetime
import time
from ..base import Options
from ..utils.time import timesince

LOG = logging.getLogger(__name__)
PLUGIN_NAME = 'testtime'


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
        from f5test.interfaces.config import ConfigInterface
        self.cfgifc = ConfigInterface()

        Plugin.configure(self, options, noseconfig)
        self.options = options
        if options.no_testtime:
            self.enabled = False

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
        c = self.cfgifc.open()
        c._attrs[PLUGIN_NAME] = Options()
        c._attrs[PLUGIN_NAME].start = datetime.datetime.now()

    def finalize(self, result):
        """Set the testrun stop time and delta.
        """
        c = self.cfgifc.open()
        c._attrs[PLUGIN_NAME].stop = datetime.datetime.now()
        c._attrs[PLUGIN_NAME].delta = c._attrs[PLUGIN_NAME].stop - \
                                     c._attrs[PLUGIN_NAME].start
        c._attrs[PLUGIN_NAME].delta_str = timesince(c._attrs[PLUGIN_NAME].start)
