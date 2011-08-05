from .base import IcontrolCommand
from .system import get_version
from ..base import  WaitableCommand
from ...base import Options

import logging
LOG = logging.getLogger(__name__) 


get_dbvar = None
class GetDbvar(WaitableCommand, IcontrolCommand):
    """Queries a DB variable.
    
    @rtype: str
    """
    
    def __init__(self, var, *args, **kwargs):
        super(GetDbvar, self).__init__(*args, **kwargs)
        self.var = var

    def setup(self):
        ic = self.api
        return ic.Management.DBVariable.query(variables=[self.var])[0]['value']


is_expired = None
class IsExpired(IcontrolCommand):
    """Checks the license expiration status.
    
    @rtype: bool
    """
    def setup(self):
        ic = self.api
        state = ic.Management.LicenseAdministration.get_evaluation_license_expiration()
        return state['current_system_time'] > state['evaluation_expire']


create_user = None
class CreateUser(IcontrolCommand):
    """Create a new user."""
    
    def __init__(self, username, password, role='ADMINISTRATOR', 
                 partition='[All]', *args, **kwargs):
        super(CreateUser, self).__init__(*args, **kwargs)
        self.username = username
        self.password = password
        self.role = role
        self.partition = partition

    def setup(self):
        ic = self.api
        v = get_version(ifc=self.ifc)
        userdata = Options()
        if 'bigip 9.0' < v < 'bigip 9.4' or 'em 1.0' < v < 'em 2.0':
            userdata.user = {}
            userdata.user.name = self.username
            userdata.user.full_name = self.username
            userdata.role = 'USER_ROLE_%s' % self.role
            userdata.password = self.password
            userdata.home_directory = '/tmp/%s' % self.username
            userdata.login_shell = '/bin/false'
            userdata.user_id = 0
            userdata.group_id = 0
            ic.Management.UserManagement.create_user(users=[userdata])
        elif 'bigip 9.4' <= v < 'bigip 10.1' or 'em 2.0' <= v < 'em 3.0':
            userdata.user = {}
            userdata.user.name = self.username
            userdata.user.full_name = self.username
            userdata.role = 'USER_ROLE_%s' % self.role
            userdata.password = {}
            userdata.password.is_encrypted = 0
            userdata.password.password = self.password
            userdata.home_directory = '/tmp/%s' % self.username
            userdata.login_shell = '/bin/false'
            userdata.user_id = 0
            userdata.group_id = 0
            ic.Management.UserManagement.create_user_2(users=[userdata])
        elif 'bigip 10.1' <= v or 'em 3.0' <= v:
            userdata.user = {}
            userdata.user.name = self.username
            userdata.user.full_name = self.username
            userdata.password = {}
            userdata.password.is_encrypted = 0
            userdata.password.password = self.password
            permission = Options()
            permission.role = 'USER_ROLE_%s' % self.role
            permission.partition = self.partition
            userdata.permissions = [permission]
            userdata.login_shell = '/bin/false'
            ic.Management.UserManagement.create_user_3(users=[userdata])
