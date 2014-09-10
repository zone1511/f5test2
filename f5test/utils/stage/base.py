'''
Created on Feb 21, 2014

@author: jono
'''


class StageError(Exception):
    pass


class Stage(object):
    name = None
    parallelizable = True
