'''
Created on May 16, 2011

@author: jono
'''
from ..config import ConfigInterface, DeviceAccess
from ...base import Interface
from ...defaults import ADMIN_USERNAME, ADMIN_PASSWORD, DEFAULT_PORTS
from .driver import RestResource


class RestInterface(Interface):
    api_class = RestResource

    def __init__(self, device=None, address=None, username=None, password=None, 
                 port=None, proto='https', timeout=90, *args, **kwargs):
        super(RestInterface, self).__init__()
        if device or not address:
            self.device = device if isinstance(device, DeviceAccess) \
                        else ConfigInterface().get_device(device)
            if username is None:
                username = self.device.get_admin_creds().username
            if password is None:
                password = self.device.get_admin_creds().password
            if address is None:
                address = self.device.address
            if port is None:
                port = self.device.ports.get(proto)
        else:
            self.device = device
        self.address = address
        self.port = port or DEFAULT_PORTS[proto]
        self.proto = proto
        self.username = username or ADMIN_USERNAME
        self.password = password or ADMIN_PASSWORD
        self.timeout = timeout
    
    def open(self): #@ReservedAssignment
        if self.api:
            return self.api

        url = "{0[proto]}://{0[username]}:{0[password]}@{0[address]}:{0[port]}".format(self.__dict__)
        self.api = self.api_class(url, timeout=self.timeout)
        return self.api
