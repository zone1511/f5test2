'''
Created on Apr 12, 2013

@author: jono
'''
from .scaffolding import Stamp


class BuiltinProfile(Stamp):
    built_in = True
    context = 'all'

    def __init__(self, name):
        self.name = name
        super(BuiltinProfile, self).__init__()

    def get_vs_profile(self):
        v = self.folder.context.version
        if v.product.is_bigip and v >= 'bigip 11.0.0':
            key = self.folder.SEPARATOR.join((self.folder.key(), self.name))
            return {key: {'context': self.context}}
        else:
            return self.name


class ServerSsl(BuiltinProfile):
    context = 'serverside'


class ClientSsl(BuiltinProfile):
    context = 'clientside'
