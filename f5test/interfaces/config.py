from ..base import Interface
from ..defaults import ADMIN_PASSWORD, ADMIN_USERNAME, ROOT_PASSWORD, \
    ROOT_USERNAME
from ..utils import net
from nose.config import _bool
import logging
import os
import time

LOG = logging.getLogger(__name__)
REACHABLE_HOST = 'f5net.com'
NOTADUT_TAG = 'not-a-dut'

class ConfigError(Exception):
    """Base exception for all exceptions raised in module config."""
    pass

class ConfigNotLoaded(ConfigError):
    """The nose test-config plugin was not loaded."""
    pass

class DeviceDoesNotExist(ConfigError):
    """Device alias requested doesn't exist."""
    pass


def expand_devices(specs, section='devices'):
    devices = specs.get(section) or []
    if '^all' in devices:
        cfgifc = ConfigInterface()
        devices = [x.alias for x in cfgifc.get_all_devices()]
    return devices


class DeviceCredential(object):
    
    def __init__(self, username, password):
        self.username = username
        
        if isinstance(password, (set, list, tuple)):
            password = set(password)
            password.discard(None)
        
        self.password = password
    
    def __repr__(self):
        return "%s:%s" % (self.username, self.password)


class DeviceAccess(object):
    
    def __init__(self, address, credentials=None, alias=None, hostname=None, 
                 discover_address=None, tags=None, groups=None):
        self.address = address
        self.credentials = credentials
        self.alias = alias
        self.hostname = hostname
        self.discover_address = discover_address
        self.tags = tags or set([])
        self.groups = groups or set([])
    
    def __repr__(self):
        return "%s:%s:[%s]" % (self.alias, self.address, self.credentials)

    def get_by_username(self, username):
        for cred in self.credentials.values():
            if cred.username == username:
                return cred

    def get_admin_creds(self):
        return self.credentials[ADMIN_USERNAME]

    def get_root_creds(self):
        return self.credentials[ROOT_USERNAME]

    def get_address(self):
        return self.address

    def get_discover_address(self):
        return self.discover_address or self.address

    def get_hostname(self):
        return self.hostname

    def get_alias(self):
        return self.alias

    def set_tags(self, tags):
        if isinstance(tags, (basestring, int)):
            self.tags = self.tags.union([tags])
        elif isinstance(tags, (list, tuple, set)):
            self.tags = self.tags.union(tags)

    def set_groups(self, groups):
        if isinstance(groups, (basestring, int)):
            self.groups = self.groups.union([groups])
        elif isinstance(groups, (list, tuple, set)):
            self.groups = self.groups.union(groups)

class Session(object):
    
    def __init__(self, config):
        self.config = config
        self.level1 = time.strftime("%Y%m%d")
        self.level2 = time.strftime("%H%M%S")
        self.name = "session-%s-%s" % (self.level1, self.level2)
        session = os.path.join('session-%s' % self.level1, self.level2)
        self.session = session
        
        path = os.path.join(self.config.paths.logs, session)
        path = os.path.expanduser(path)
        path = os.path.expandvars(path)
        self.path = path
        
        # Logging at CRITICAL level hoping that it gets redirected the console. 
        LOG.critical('Session %s initialized.', self.name)
        LOG.critical('Session path: %s', self.path)
        local_ip = net.get_local_ip(REACHABLE_HOST)
        LOG.critical('Session URL: %s', self.get_url(local_ip))

    def get_url(self, local_ip):
        #local_ip = net.get_local_ip(peer)
        url = self.config.paths.sessionurl % dict(runner=local_ip, 
                                                  session=self.session)
        return url

class ConfigInterface(Interface):
    
    def __init__(self, _config=None):
        from f5test.noseplugins.testconfig import config
        
        self.config = _config or config
        if not self.config:
            raise ConfigNotLoaded("Is nose-testconfig plugin loaded?")
        super(ConfigInterface, self).__init__()

    def open(self): #@ReservedAssignment
        self.api = self.config
        return self.config

    def get_default_key(self, collection):
        return filter(lambda x:_bool(x[1] and x[1].get('default')), 
                      collection.items())[0][0]

    def get_default_value(self, collection):
        return filter(lambda x:_bool(x.get('default')), 
                      collection.values())[0]
    
    def get_device(self, device=None, all_passwords=False, lock=True):
        
        if device is None:
            device = self.get_default_key(self.config['devices'])
        
        try:
            specs = self.config['devices'][device]
            if not specs:
                return
        except KeyError:
            raise DeviceDoesNotExist(device)

        if all_passwords:
            admin_passwords = set((specs.get('lock admin password'),
                             specs.get('admin password'),
                             specs.get('default admin password', ADMIN_PASSWORD)
                        ))
            root_passwords = set((specs.get('lock root password'),
                             specs.get('root password'),
                             specs.get('default root password', ROOT_PASSWORD)
                        ))
        else:
            if _bool(self.config.isbvt):
                admin_passwords = lock and specs.get('lock admin password') or \
                                  specs.get('admin password', ADMIN_PASSWORD)
                root_passwords = lock and specs.get('lock root password') or \
                                 specs.get('root password', ROOT_PASSWORD)
            else:
                admin_passwords = specs.get('admin password', ADMIN_PASSWORD)
                root_passwords = specs.get('root password', ROOT_PASSWORD)
        
        admin = DeviceCredential(specs.get('admin username', ADMIN_USERNAME), 
                                 admin_passwords)
        root = DeviceCredential(specs.get('root username', ROOT_USERNAME), 
                                root_passwords)
        
        return DeviceAccess(net.resolv(specs['address']),
                            credentials={ADMIN_USERNAME:admin, ROOT_USERNAME:root},
                            alias=device, hostname=specs['address'],
                            discover_address=specs.get('discover address'),
                            tags=specs.get('tags'))

    def get_device_by_address(self, address):
        for device in self.get_all_devices():
            if device.address == address or device.discover_address == address:
                return device
        raise DeviceDoesNotExist("A device with IP address of '%s' cannot be found" % address)

    def get_device_address(self, device):
        device_access = self.get_device(device)
        return device_access.address

    def get_device_admin_creds(self, device, *args, **kwargs):
        device_access = self.get_device(device, *args, **kwargs)
        return device_access.get_admin_creds()

    def get_device_root_creds(self, device, *args, **kwargs):
        device_access = self.get_device(device, *args, **kwargs)
        return device_access.get_root_creds()

    def get_all_devices(self, all_passwords=False, lock=True):
        for device in self.config.devices:
            device = self.get_device(device, all_passwords=all_passwords, lock=lock)
            if device and NOTADUT_TAG not in device.tags:
                yield device

    def get_selenium_head(self, head=None):
        if head is None:
            head = self.get_default_key(self.config['selenium'])

        return head, self.config['selenium'][head]

    def get_session(self):
        if not self.config._session:
            self.config._session = Session(self.config)
        return self.config._session
