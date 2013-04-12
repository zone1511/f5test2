from .. import base
from ...interfaces.rest import RestInterface
import logging

LOG = logging.getLogger(__name__)


class RestCommand(base.Command):
    """Base class for Rest Commands.

    @param device: a device alias from config
    @type device: str
    @param api: an opened underlying interface
    @type api: Icontrol
    @param address: IP address or hostname
    @type address: str
    @param username: the admin username
    @type username: str
    @param password: the admin password
    @type password: str
    """
    def __init__(self, device=None, ifc=None, address=None, username=None,
                 password=None, proto='https', port=None, timeout=90,
                 *args, **kwargs):
        if ifc is None:
            self.ifc = RestInterface(device, address, username, password,
                                     proto=proto, port=port, timeout=timeout)
            self.api = self.ifc.open()
            self._keep_alive = False
        else:
            self.ifc = ifc
            self._keep_alive = True

        super(RestCommand, self).__init__(*args, **kwargs)

    def __repr__(self):
        parent = super(RestCommand, self).__repr__()
        opt = {}
        opt['address'] = self.ifc.address
        opt['username'] = self.ifc.username
        opt['password'] = self.ifc.password
        opt['port'] = self.ifc.port
        return parent + "(address=%(address)s port=%(port)s username=%(username)s " \
                        "password=%(password)s)" % opt

    def prep(self):
        if not self.ifc.is_opened():
            self.ifc.open()
            #self.api.connect()
        self.api = self.ifc.api

    def cleanup(self):
        if not self._keep_alive:
            self.ifc.close()
