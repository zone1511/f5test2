'''
Created on Aug 29, 2014

@author: jono
'''
import logging

from . import ExtendedPlugin

STDOUT = logging.getLogger('stdout')


class Start(ExtendedPlugin):
    """
    Log when the session has started (after all plugins are configured).
    """
    enabled = True
    score = 1000

    def begin(self):
        STDOUT.info('Started.')
