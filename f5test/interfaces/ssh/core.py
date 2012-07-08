"""Friendly Python SSH2 interface."""

from .driver import Connection
from ..config import ConfigInterface, DeviceAccess
from ...base import Interface
from ...defaults import ROOT_USERNAME, ROOT_PASSWORD, DEFAULT_PORTS


class SSHInterface(Interface):
    
    def __init__(self, device=None, address=None, username=None, password=None, 
                 port=None, timeout=180, *args, **kwargs):
        super(SSHInterface, self).__init__()
        if device or not address:
            self.device = device if isinstance(device, DeviceAccess) \
                        else ConfigInterface().get_device(device)
            if username is None:
                username = self.device.get_root_creds().username
            if password is None:
                password = self.device.get_root_creds().password
            if address is None:
                address = self.device.address
            if port is None:
                port = self.device.ports.get('ssh')
        else:
            self.device = device
        self.address = address
        self.username = username or ROOT_USERNAME
        self.password = password or ROOT_PASSWORD
        self.port = port or DEFAULT_PORTS['ssh']
        self.timeout = timeout

    def is_opened(self):
        return self.api and self.api.is_connected()

    @property
    def version(self):
        from ...commands.shell.ssh import get_version
        return get_version(ifc=self)

    def open(self): #@ReservedAssignment
        if self.is_opened():
            return self.api
        address = self.address
        username = self.username
        password = self.password

        api = Connection(address, username, password, port=self.port,
                         timeout=self.timeout, look_for_keys=True) # Try pubkeyauth first.
        api.connect()
        self.api = api
        return api

    def close(self, *args, **kwargs):
        if self.is_opened():
            self.api.close()
        super(SSHInterface, self).close()
