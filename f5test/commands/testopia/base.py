from .. import base
from ...interfaces.testopia import TestopiaInterface
import logging

LOG = logging.getLogger(__name__) 


class TestopiaCommand(base.Command):
    """Base class for Testopia Commands. If api argument is provided it will
    reuse the opened interface otherwise it will open/close a new interface
    using the address, username and password parameters. 
    
    @param api: an opened underlying interface
    @type api: Testopia
    @param address: IP address or hostname
    @type address: str
    @param username: the bugzilla username
    @type username: str
    @param password: the bugzilla password
    @type password: str
    """
    def __init__(self, api=None,
                address=None, username=None, password=None, *args, **kwargs):
        super(TestopiaCommand, self).__init__(*args, **kwargs)
        
        self.api = api
        if not api:
            self.interface = TestopiaInterface(address, username, password)

    def __repr__(self):
        parent = super(TestopiaCommand, self).__repr__()
        opt = {}
        opt['address'] = self.api.hostname
        opt['username'] = self.api.username
        opt['password'] = self.api.password
        return parent + "(address=%(address)s username=%(username)s " \
                        "password=%(password)s)" % opt

    def prep(self):
        """Open a new interface if none is provided"""
        if not self.api:
            self.api = self.interface.open()

    def cleanup(self):
        """Testopia interface is not persistent, so we don't need to close it"""
        pass
