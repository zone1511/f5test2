from ..config import ConfigInterface, DeviceAccess
from .driver import Icontrol
from ...base import Interface
from ...defaults import ADMIN_USERNAME, ADMIN_PASSWORD
import logging

LOG = logging.getLogger(__name__)


class IcontrolInterface(Interface):
    
    def __init__(self, device=None, address=None, 
                 username=ADMIN_USERNAME, password=ADMIN_PASSWORD, 
                 timeout=90, debug=False, *args, **kwargs):
        super(IcontrolInterface, self).__init__()
        if device or not address:
            self.device = device if isinstance(device, DeviceAccess) \
                        else ConfigInterface().get_device(device)
        else:
            self.device = device
        self.address = address
        self.username = username
        self.password = password
        self.timeout = timeout
        self.debug = int(debug)
    
    def __str__(self):
        if isinstance(self.device, DeviceAccess):
            return self.device.address
        return self.address or 'icontrol'
        
    @property
    def version(self):
        from ...commands.icontrol.system import get_version
        return get_version(ifc=self)

    def set_session(self, session=None):
        v = self.version
        if v.product.is_bigip and v >= 'bigip 11.0':
            if not session:
                session = self.api.System.Session.get_session_identifier()
            LOG.debug('iControl session: %s', session)
            self.api = Icontrol(self.address, self.username, self.password, 
                                timeout=self.timeout, session=session, 
                                debug=self.debug)
        return session

    def set_extra_query(self, query=None):
        LOG.debug('iControl query: %s', query)
        self.api.query = query

    def open(self):
        if self.api:
            return self.api
        if self.device or not self.address:
            device = self.device
            address = device.address
            username = device.get_admin_creds().username
            password = device.get_admin_creds().password
            self.device = device.get_alias()
            self.address = address
            self.username = username
            self.password = password
        else:
            address = self.address
            username = self.username
            password = self.password

        self.api = Icontrol(address, username, password, timeout=self.timeout,
                            debug=self.debug)
        return self.api
