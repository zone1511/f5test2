'''
Created on Sep 24, 2012

@author: jono
@contact: http://code.google.com/p/python-nose/issues/detail?id=255
'''
"""
This plugin randomizes the order of tests within a unittest.TestCase class
"""
__test__ = False

import logging
from nose.plugins import Plugin
import random

log = logging.getLogger(__name__)


class Randomize(Plugin):
    """
    Randomize the order of the tests within a unittest.TestCase class
    """
    name = 'randomize'
    # Generate a seed for deterministic behaviour
    # Could use getstate  and setstate, but that would involve
    # pickling the state and storing it somewhere. too lazy.
    seed = random.getrandbits(32)

    def options(self, parser, env):
        """Register commandline options.
        """
        Plugin.options(self, parser, env)
        parser.add_option('--randomize', action='store_true', dest='randomize',
                          help="Randomize the order of the tests within a unittest.TestCase class")
        parser.add_option('--seed', action='store', dest='seed', default=None, type=int,
                          help="Initialize the seed for deterministic behavior in reproducing failed tests")

    def configure(self, options, conf):
        """
        Configure plugin.
        """
        Plugin.configure(self, options, conf)
        if options.randomize:
            self.enabled = True
            if options.seed is not None:
                self.seed = options.seed
            random.seed(self.seed)
            log.info("Using %d as seed" % self.seed)

    def prepareTestLoader(self, loader):
        loader.sortTestMethodsUsing = lambda x, y: random.choice([-1, 1])
