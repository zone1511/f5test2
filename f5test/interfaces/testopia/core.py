from ..config import ConfigInterface
from .driver import Testopia
from ...base import Interface
import urlparse


class TestopiaInterface(Interface):
    
    def __init__(self, address=None, username=None, password=None, 
                 timeout=90, *args, **kwargs):
        super(TestopiaInterface, self).__init__()
        
        self.address = address
        self.username = username
        self.password = password
        self.timeout = timeout
    
    def open(self): #@ReservedAssignment
        if not self.api is None:
            return self.api

        if not self.address:
            config = ConfigInterface().open()
            testopia = config.testopia
            url = urlparse.urljoin(testopia.address, testopia.uri)
            self.address = url
            self.username = self.username or testopia.username
            self.password = self.password or testopia.password

        address = self.address
        username = self.username
        password = self.password

        self.api = Testopia(address, username, password, timeout=self.timeout)
        return self.api
