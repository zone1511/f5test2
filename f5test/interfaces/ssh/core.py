"""Friendly Python SSH2 interface."""

from .driver import Connection
from ..config import ConfigInterface, DeviceAccess
from ...base import Interface
from ...defaults import ROOT_USERNAME, ROOT_PASSWORD


class SSHInterface(Interface):
    
    def __init__(self, device=None, address=None, username=ROOT_USERNAME, 
                 password=ROOT_PASSWORD, timeout=180, *args, **kwargs):
        super(SSHInterface, self).__init__()
        if device or not address:
            self.device = device if isinstance(device, DeviceAccess) \
                        else ConfigInterface().get_device(device)
        else:
            self.device = device
        self.address = address
        self.username = username
        self.password = password
        self.timeout = timeout

    def __str__(self):
        if isinstance(self.device, DeviceAccess):
            return self.device.address
        return self.address or 'ssh'

    def is_opened(self):
        return self.api and self.api.is_connected()

    @property
    def version(self):
        from ...commands.shell.ssh import get_version
        return get_version(ifc=self)

    def open(self):
        if self.is_opened():
            return self.api
        if self.device or not self.address:
            device = self.device
            address = device.address
            username = device.get_root_creds().username
            password = device.get_root_creds().password
            self.address = address
            self.username = username
            self.password = password
        else:
            address = self.address
            username = self.username
            password = self.password

        api = Connection(address, username, password, timeout=self.timeout,
                         look_for_keys=True) # Try pubkeyauth first.
        api.connect()
        self.api = api
        return api

    def close(self, *args, **kwargs):
        if self.is_opened():
            self.api.close()
        super(SSHInterface, self).close()
