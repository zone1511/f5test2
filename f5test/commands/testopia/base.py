from .. import base
from ...interfaces.xmlrpc import BugzillaInterface
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
    def __init__(self, ifc=None, address=None, username=None, password=None,
                 *args, **kwargs):
        if ifc is None:
            self.ifc = BugzillaInterface(address, username, password)
            self.api = self.ifc.open()
            self._keep_alive = False
        else:
            self.ifc = ifc
            self._keep_alive = True

        super(TestopiaCommand, self).__init__(*args, **kwargs)

    def __repr__(self):
        parent = super(TestopiaCommand, self).__repr__()
        opt = {}
        opt['address'] = self.ifc.address
        opt['username'] = self.ifc.username
        opt['password'] = self.ifc.password
        return parent + "(address=%(address)s username=%(username)s " \
                        "password=%(password)s)" % opt

    def prep(self):
        """Open a new interface if none is provided"""
        if not self.ifc.is_opened():
            self.ifc.open()
        self.api = self.ifc.api

    def cleanup(self):
        """Testopia interface is not persistent, so we don't need to close it"""
        if not self._keep_alive:
            self.ifc.close()
