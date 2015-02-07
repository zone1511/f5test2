#!/usr/bin/env python
"""
Use this class to access Bugzilla or Testopia via XML-RPC
"""

__version__ = "2.0"

from ...base import AttrDict
from cookielib import CookieJar
import logging
import xmlrpclib
import sys

DEFAULT_TIMEOUT = 90
LOG = logging.getLogger(__name__)

# AttrDict is basically a dict, but xmlrpclib doesn't know about it.
# Monkey patch it here.
xmlrpclib.Marshaller.dispatch[AttrDict] = xmlrpclib.Marshaller.dispatch[dict]


# Monkey patch the XmlRpc parser to return AttrDicts instead
class _Method:
    # some magic to bind an XML-RPC method to an RPC server.
    # supports "nested" methods (e.g. examples.getStateName)
    def __init__(self, send, name):
        self.__send = send
        self.__name = name

    def __getattr__(self, name):
        return _Method(self.__send, "%s.%s" % (self.__name, name))

    def __call__(self, *args):
        return AttrDict(self.__send(self.__name, args))
xmlrpclib._Method = _Method


class XmlRpc(xmlrpclib.ServerProxy):
    """Initialize the XmlRpc driver.

    @param url: the URL of the XML-RPC interface
    @type url: str
    @param username: the account to log into Testopia such as jdoe@mycompany.com
    @type username: str
    @param password: the password associated with the username
    @type password: str
    @param timeout: transport timeout in seconds
    @type timeout: int

    Example: t = Testopia('jdoe@mycompany.com',
                          'jdoepassword'
                          'https://myhost.mycompany.com/bugzilla/tr_xmlrpc.cgi')
    """

    def __init__(self, url, timeout=DEFAULT_TIMEOUT, *args, **kwargs):

        if sys.version_info[0:2] < (2, 7):
            from .transport_26 import SafeCookieTransport, CookieTransport  # @UnusedImport
        else:
            from .transport_27 import SafeCookieTransport, CookieTransport  # @Reimport

        if url.startswith('https://'):
            transport = SafeCookieTransport(timeout=timeout)
        elif url.startswith('http://'):
            transport = CookieTransport(timeout=timeout)
        else:
            raise ValueError("Unrecognized URL scheme")

        transport.cookiejar = CookieJar()
        xmlrpclib.ServerProxy.__init__(self, url, transport=transport,
                                       *args, **kwargs)

    def __nonzero__(self):
        return 1
