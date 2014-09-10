from .. import base
from ...interfaces.icontrol import IcontrolInterface
import logging

LOG = logging.getLogger(__name__)


class IcontrolCommand(base.Command):
    """Base class for Icontrol Commands. If api argument is provided it will
    reuse the opened interface otherwise it will open/close a new interface
    using the address, username and password parameters.

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
            self.ifc = IcontrolInterface(device, address, username, password,
                                         proto=proto, port=port, timeout=timeout)
            self.api = self.ifc.open()
            self._keep_alive = False
        else:
            self.ifc = ifc
            self._keep_alive = True

        super(IcontrolCommand, self).__init__(*args, **kwargs)

    def __repr__(self):
        parent = super(IcontrolCommand, self).__repr__()
        opt = {}
        opt['address'] = self.ifc.address
        opt['username'] = self.ifc.username
        opt['password'] = self.ifc.password
        opt['port'] = self.ifc.port
        return parent + "(address=%(address)s port=%(port)s username=%(username)s " \
                        "password=%(password)s)" % opt

    def prep(self):
        super(IcontrolCommand, self).prep()
        if not self.ifc.is_opened():
            self.ifc.open()
        self.api = self.ifc.api

    def cleanup(self):
        if not self._keep_alive:
            self.ifc.close()
        return super(IcontrolCommand, self).cleanup()
