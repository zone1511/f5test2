from ..base import Interface, Options
from ..defaults import ADMIN_PASSWORD, ADMIN_USERNAME, ROOT_PASSWORD, \
    ROOT_USERNAME, DEFAULT_PORTS
from ..utils import net
from ..compat import _bool
import copy
import logging
import os
import time

LOG = logging.getLogger(__name__)
STDOUT = logging.getLogger('stdout')
REACHABLE_HOST = 'f5net.com'
NOTADUT_TAG = 'not-a-dut'
KEYSET_DEFAULT = 0
KEYSET_COMMON = 1
KEYSET_LOCK = 2

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
    devices = []
    cfgifc = ConfigInterface()
    for device in specs.get(section) or []:
        if device == '^all':
            devices += list(cfgifc.get_all_devices())
        else:
            devices.append(cfgifc.get_device(device))
    return set(devices)


class DeviceCredential(object):
    
    def __init__(self, username, passwords):
        """
        @param username: The username
        @type username: str
        @param password: The password(s)
        @type password: dict
        """
        self.username = username
        if isinstance(passwords, basestring):
            passwords = Options({'default':passwords})
        self.passwords = passwords
        self.password = passwords.default
    
    def __repr__(self):
        return "%s:%s" % (self.username, self.password)


class DeviceAccess(object):
    
    def __init__(self, address, credentials=None, alias=None, specs=None):
        self.address = address
        self.credentials = credentials
        self.alias = alias
        self.specs = specs or {}
        self.tags = set([])
        self.groups = set([])
        self.hostname = self.specs.get('address')
        self.discover_address = self.specs.get('discover address')
        self.set_tags(self.specs.get('tags'))
        self.set_groups(self.specs.get('groups'))
        self.ports = copy.copy(DEFAULT_PORTS)
        self.ports.update(self.specs.get('ports', {}))
        self.specs.setdefault('_keyset', KEYSET_COMMON)
    
    def __repr__(self):
        return "%s:%s:[%s]" % (self.alias, self.address, self.credentials)

    def is_default(self):
        return _bool(self.specs.get('default'))

    def get_by_username(self, username):
        for cred in self.credentials.values():
            if cred.username == username:
                return cred

    def get_user_creds(self, username, keyset=None):
        creds = self.credentials[username]
        if keyset is None:
            keyset = self.specs.get('_keyset', KEYSET_DEFAULT)
        
        if keyset == KEYSET_LOCK:
            creds.password = creds.passwords.lock or creds.passwords.common or \
                             creds.passwords.default
        elif keyset == KEYSET_COMMON:
            creds.password = creds.passwords.common or creds.passwords.default
        else:
            creds.password = creds.passwords.default

        return creds

    def get_admin_creds(self, *args, **kwargs):
        return self.get_user_creds(username=ADMIN_USERNAME, *args, **kwargs)

    def get_root_creds(self, *args, **kwargs):
        return self.get_user_creds(username=ROOT_USERNAME, *args, **kwargs)

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
        
        if self.config.paths and self.config.paths.logs:
            path = os.path.join(self.config.paths.logs, session)
            path = os.path.expanduser(path)
            path = os.path.expandvars(path)
            self.path = path
        else:
            self.path = None
        
        STDOUT.info('Session %s initialized.', self.name)
        if self.path:
            STDOUT.info('Session path: %s', self.path)
        
        local_ip = net.get_local_ip(REACHABLE_HOST)
        url = self.get_url(local_ip)
        if url:
            STDOUT.info('Session URL: %s', url)

    def get_url(self, local_ip=None):
        #local_ip = net.get_local_ip(peer)
        if self.config.paths and self.config.paths.sessionurl:
            url = self.config.paths.sessionurl % dict(runner=local_ip, 
                                                      session=self.session)
            return url

class ConfigInterface(Interface):
    
    def __init__(self, data=None):
        from f5test.noseplugins.testconfig import CONFIG
        
        self.config = data if data else getattr(CONFIG, 'data', None)
        if not self.config:
            raise ConfigNotLoaded("Is nose-testconfig plugin loaded?")
        
        # Set an empty private container for inter-test/plugin exchange.
        self.config.setdefault('_attrs', Options())
        super(ConfigInterface, self).__init__()

    def get_config(self):
        return self.config
    
    def set_global_config(self):
        from f5test.noseplugins.testconfig import CONFIG
        
        setattr(CONFIG, 'data', self.get_config())
    
    def open(self): #@ReservedAssignment
        self.api = self.get_config()
        return self.api

    def get_default_key(self, collection):
        return filter(lambda x:_bool(x[1] and x[1].get('default')), 
                      collection.items())[0][0]

    def get_default_value(self, collection):
        return filter(lambda x:_bool(x.get('default')), 
                      collection.values())[0]
    
    def get_device(self, device=None):
        
        if isinstance(device, DeviceAccess):
            return device
        
        if device is None:
            device = self.get_default_key(self.config['devices'])
        
        try:
            specs = self.config['devices'][device]
            if not specs:
                return
        except KeyError:
            raise DeviceDoesNotExist(device)

        admin_passwords = Options()
        admin_passwords.lock = specs.get('lock admin password')
        admin_passwords.common = specs.get('admin password')
        admin_passwords.default = ADMIN_PASSWORD
        
        root_passwords = Options()
        root_passwords.lock = specs.get('lock root password')
        root_passwords.common = specs.get('root password')
        root_passwords.default = ROOT_PASSWORD

        admin = DeviceCredential(specs.get('admin username', ADMIN_USERNAME), 
                                 admin_passwords)
        root = DeviceCredential(specs.get('root username', ROOT_USERNAME), 
                                root_passwords)
        
        return DeviceAccess(net.resolv(specs['address']),
                            credentials={ADMIN_USERNAME:admin,
                                         ROOT_USERNAME:root},
                            alias=device, specs=specs)

    def get_device_by_address(self, address):
        for device in self.get_all_devices():
            if device.address == address or device.discover_address == address:
                return device
        LOG.warning('A device with address %s was NOT found in the configuration!', address)

    def get_device_address(self, device):
        device_access = self.get_device(device)
        return device_access.address

    def get_all_devices(self):
        for device in self.config.devices:
            device = self.get_device(device)
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
