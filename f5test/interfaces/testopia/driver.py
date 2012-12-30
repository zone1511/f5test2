#!/usr/bin/env python
"""
Use this class to access Testopia via XML-RPC

from testopia import Testopia

Or, more directly:
t = Testopia('jdoe@mycompany.com',
             'jdoepassword',
             'https://myhost.mycompany.com/bugzilla/tr_xmlrpc.cgi')
t.TestPlan.get(10)
"""

__version__ = "0.1"

from cookielib import CookieJar
import logging
import xmlrpclib
import sys

DEFAULT_TIMEOUT = 90
LOG = logging.getLogger(__name__)


#class TestopiaError(Exception):
#    pass
#
#
#class TestopiaXmlrpcError(Exception):
#    def __init__(self, verb, params, wrappedError):
#        self.verb = verb
#        self.params = params
#        self.wrappedError = wrappedError
#
#    def __str__(self):
#        return "Error while executing cmd '%s' --> %s" \
#               % (self.verb + "(" + self.params + ")", self.wrappedError)


class Testopia(xmlrpclib.ServerProxy):
    """Initialize the Testopia driver.

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

    def __init__(self, url, username, password, timeout=DEFAULT_TIMEOUT,
                 *args, **kwargs):
        
        if sys.version_info[0:2] < (2, 7):
            from .transport_26 import SafeCookieTransport, CookieTransport #@UnusedImport
        else:
            from .transport_27 import SafeCookieTransport, CookieTransport #@Reimport

        if url.startswith('https://'):
            transport = SafeCookieTransport(timeout=timeout)
        elif url.startswith('http://'):
            transport = CookieTransport(timeout=timeout)
        else:
            raise "Unrecognized URL scheme"
        
        transport.cookiejar = CookieJar()
        xmlrpclib.ServerProxy.__init__(self, url, transport=transport,
                                       *args, **kwargs)

        # Login, get a cookie into our cookie jar:
        ret = self.User.login(dict(login=username, password=password))
        # Record the user ID in case the script wants this
        self.user_id = ret['id']

    def __nonzero__(self):
        return 1
