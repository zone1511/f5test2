'''
Created on Jun 23, 2011

@author: jono
'''
from __future__ import absolute_import
from nose.plugins.base import Plugin
import logging
import time
#from ..base import AttrDict

LOG = logging.getLogger(__name__)


class TestTime(Plugin):
    enabled = True
    name = "testtime"
    score = 517

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--no-testtime', action='store_true',
                          dest='no_testtime', default=False,
                          help="Disable TestTime reporting. (default: no)")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """

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
