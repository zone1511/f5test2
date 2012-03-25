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
        config = ConfigInterface().open()
        testopia = config.testopia
        url = urlparse.urljoin(testopia.address, testopia.uri)
        address = self.address or url
        username = self.username or testopia.username
        password = self.password or testopia.password

        self.api = Testopia(address, username, password, timeout=self.timeout)
        return self.api

