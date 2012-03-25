'''
Created on May 16, 2011

@author: jono
'''
from ..config import ConfigInterface, DeviceAccess
from ...base import Interface
from ...defaults import ADMIN_USERNAME, ADMIN_PASSWORD
from .driver import RestResource


class RestInterface(Interface):
    api_class = RestResource

    def __init__(self, device=None, address=None, username=None, password=None, 
                 timeout=90, ssl=True, *args, **kwargs):
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
        else:
            self.device = device
        self.address = address
        self.username = username or ADMIN_USERNAME
        self.password = password or ADMIN_PASSWORD
        self.timeout = timeout
        self.ssl = ssl
    
    def open(self): #@ReservedAssignment
        if self.api:
            return self.api
        address = self.address
        username = self.username
        password = self.password

        url = ("https" if self.ssl else "http") + "://%s:%s@%s" % (username, 
                                                                   password, 
                                                                   address)
        self.api = self.api_class(url, timeout=self.timeout)
        return self.api
