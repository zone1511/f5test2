'''
Created on Jan 6, 2014

@author: jono
'''
from ...base import Interface
from ..config import ConfigInterface, DeviceAccess
from ...defaults import DEFAULT_PORTS, ADMIN_USERNAME
from .driver import SNMPWrap, cmdgen
import logging

LOG = logging.getLogger(__name__)
PROTO = 'snmp'


class SnmpInterface(Interface):

    def __init__(self, device=None, address=None, username=None, port=None,
                 timeout=1, version=2, community='public',
                 # v3 args
                 auth=None, priv=None,
                 auth_protocol=cmdgen.usmNoAuthProtocol,
                 priv_protocol=cmdgen.usmNoPrivProtocol,
                 *args, **kwargs):
        super(SnmpInterface, self).__init__()
        if device or not address:
            self.device = device if isinstance(device, DeviceAccess) \
                        else ConfigInterface().get_device(device)
            if username is None:
                username = self.device.get_admin_creds().username
            if address is None:
                address = self.device.address
            if port is None:
                port = self.device.ports.get(PROTO)
        else:
            self.device = device
        self.address = address
        self.username = username or ADMIN_USERNAME
        self.port = port or DEFAULT_PORTS[PROTO]
        self.version = version
        self.community = community
        self.timeout = timeout
        self.auth = auth
        self.priv = priv
        self.auth_protocol = auth_protocol
        self.priv_protocol = priv_protocol

    def __repr__(self):
        name = self.__class__.__name__
        return "<{0}: {1.username}:{1.auth}:{1.priv}@{1.address}:{1.port}/{1.community}>".format(name, self)

    def open(self):  # @ReservedAssignment
        if self.api:
            return self.api
        address = self.address

        self.api = SNMPWrap(address, self.port, self.timeout,
                            version=self.version, community=self.community,
                            username=self.username,
                            auth=self.auth, priv=self.priv,
                            auth_protocol=self.auth_protocol,
                            priv_protocol=self.priv_protocol)
        return self.api
