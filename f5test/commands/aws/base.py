'''
Created on Feb 21, 2014

@author: a.dobre@f5.com
'''
from .. import base


class AWSCommand(base.Command):

    def __init__(self, ifc, *args, **kwargs):
        self.ifc = ifc
        if self.ifc is None:
            raise TypeError('AWS interface cannot be None.')
        assert self.ifc.is_opened()
        self.api = self.ifc.api

        super(AWSCommand, self).__init__(*args, **kwargs)
