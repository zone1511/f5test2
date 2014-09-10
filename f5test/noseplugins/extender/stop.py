'''
Created on Aug 29, 2014

@author: jono
'''
import logging

from . import ExtendedPlugin

STDOUT = logging.getLogger('stdout')


class Stop(ExtendedPlugin):
    """
    Log when the session has stopped.
    """
    enabled = True
    score = 1

    def finalize(self, result):
        STDOUT.info('Completed.')
