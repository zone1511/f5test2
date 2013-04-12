'''
Created on Jun 10, 2011

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options
import logging
import os

LOG = logging.getLogger(__name__)


class ConfigGenerator(Macro):

    def setup(self):
        ctx = Options()

if __name__ == '__main__':
    ConfigGenerator().run()
