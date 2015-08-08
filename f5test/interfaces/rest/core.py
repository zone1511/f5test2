'''
Created on May 16, 2011

@author: jono
'''
from ..config import ConfigInterface, DeviceAccess, DEFAULT_ROLE
from ...base import Interface
from ...defaults import DEFAULT_PORTS
from .driver import RestResource
from ...base import enum
import urllib
import urlparse

AUTH = enum('NONE', 'BASIC', 'TOKEN')


class RestInterface(Interface):
    api_class = RestResource
    creds_role = DEFAULT_ROLE

    def __init__(self, device=None, address=None, username=None, password=None,
                 port=None, proto='https', timeout=90, auth=AUTH.BASIC, url=None,
                 *args, **kwargs):
        super(RestInterface, self).__init__()

        if url:
            bits = urlparse.urlparse(url)

            if bits.username and bits.password:
                auth = AUTH.BASIC
            else:
                auth = AUTH.NONE

            if bits.scheme:
                proto = bits.scheme
            if bits.hostname:
                address = bits.hostname
            if bits.port:
                port = bits.port
            if bits.username:
                username = bits.username
            if bits.password:
                password = bits.password
            if bits.query:
                params = urlparse.parse_qs(bits.query)
                if params.get('timeout'):
                    timeout = params['timeout'][0]

        self.device = device if isinstance(device, DeviceAccess) \
            else ConfigInterface().get_device(device)

        if self.device:
            if username is None:
                username = self.device.get_creds(self.creds_role).username
            if password is None:
                password = self.device.get_creds(self.creds_role).password
            if address is None:
                address = self.device.address
            if port is None:
                port = self.device.ports.get(proto)

        self.address = address
        self.port = port or DEFAULT_PORTS[proto]
        self.proto = proto
        self.username = username
        self.password = password
        self.timeout = timeout
        self.auth = auth

    def __repr__(self):
        name = self.__class__.__name__
        return "<{0}: {1.proto}://{1.username}:{1.password}@{1.address}:{1.port}/?timeout={1.timeout}&auth={1.auth}>".format(name, self)

    def open(self):  # @ReservedAssignment
        if self.is_opened():
            return self.api

        if self.auth == AUTH.BASIC:
            quoted = dict(map(lambda (k, v): (k, urllib.quote_plus(str(v))),
                              self.__dict__.iteritems()))
            url = "{0[proto]}://{0[username]}:{0[password]}@{0[address]}:{0[port]}".format(quoted)
            self.api = self.api_class(url, timeout=self.timeout)
            return self.api
        elif self.auth == AUTH.NONE:
            quoted = dict(map(lambda (k, v): (k, urllib.quote_plus(str(v))),
                              self.__dict__.iteritems()))
            url = "{0[proto]}://{0[address]}:{0[port]}".format(quoted)
            self.api = self.api_class(url, timeout=self.timeout)
            return self.api
        else:
            raise NotImplementedError('Unsupported auth type: %s' % self.auth)

    # 07/11/2013 - Ionut
    # WARNING: This is a hack, it's using iControl because there's no way to
    #          determine the version info through the REST API.
    @property
    def version(self):
        from ...commands.icontrol.system import get_version
        return get_version(address=self.address, username=self.username,
                           password=self.password, proto=self.proto, port=self.port)
