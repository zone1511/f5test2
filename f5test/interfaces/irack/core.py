'''
Created on May 16, 2011

@author: jono
'''
from ..config import ConfigInterface
from .driver import Irack
from ...base import Interface
import urlparse


class IrackInterface(Interface):
    
    def __init__(self, address=None, username=None, password=None, 
                 timeout=90, *args, **kwargs):
        super(IrackInterface, self).__init__()
        
        self.address = address
        self.username = username
        self.password = password
        self.timeout = timeout
    
    def open(self):
        if not self.api is None:
            return self.api

        if self.address:
            address = self.address
            username = self.username
            password = self.password
        else:
            config = ConfigInterface().open()
            section = config.irack
            url = urlparse.urljoin(section.address, section.uri)
            address = url
            username = section.username
            password = section.password

        self.api = Irack(address, username, password, timeout=self.timeout)
        return self.api

