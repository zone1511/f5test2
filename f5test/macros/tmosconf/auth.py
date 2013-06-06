'''
Created on Apr 15, 2013

@author: jono
'''
from .scaffolding import Stamp
import crypt
#import itertools
#import netaddr
from ...utils.parsers import tmsh


class User(Stamp):
    TMSH = """
        auth user %(name)s {
           encrypted-password "$1$f5site02$lULDkZ4/wBvcXq1Ek6y0l/"
           description "created by confgen"
           shell none
           role admin
           partition-access all
        }
    """
    BIGPIPE = """
        user %(name)s {
           password crypt "$1$f5site02$lULDkZ4/wBvcXq1Ek6y0l/"
           description "a"
           shell "/bin/false"
#           role administrator in all
        }
    """
    bp_role_map = {'admin': 'administrator',
                   'application-editor': 'app editor',
                   'no-access': 'none',
                   'web-application-security-editor': 'policy editor',
                   'resource-admin': 'resource admin',
                   'user-manager': 'user manager'}

    def __init__(self, name, password=None, role='admin'):
        self.name = name
        self.password = password or name
        self.role = role
        self.salt = '$1$fakesalt$'
        super(User, self).__init__()

    def tmsh(self, obj):
        key = self.folder.SEPARATOR.join((self.folder.key(), self.name))
        value = obj.rename_key('auth user %(name)s', name=self.name)
        value['encrypted-password'] = crypt.crypt(self.password, self.salt)
        value['role'] = self.role
        value['description'] = "User %s/%s" % (self.name, self.password)
        return key, obj

    def bigpipe(self, obj):
        key = self.name
        value = obj.rename_key('user %(name)s', name=self.name)
        value['password crypt'] = crypt.crypt(self.password, self.salt)
        value['role'] = tmsh.RawString(' '.join([User.bp_role_map.get(self.role, self.role), 'in all']))
        value['description'] = "User %s/%s" % (self.name, self.password)
        return key, obj
