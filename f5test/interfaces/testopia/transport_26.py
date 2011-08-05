'''
Created on Jun 6, 2011

@author: jono
'''
from cookielib import CookieJar
import logging
import urllib2
import xmlrpclib
import httplib

DEFAULT_TIMEOUT = 90
LOG = logging.getLogger(__name__)


class TimeoutHTTPConnection(httplib.HTTPConnection):
    
    def connect(self):
        httplib.HTTPConnection.connect(self)
        self.sock.settimeout(self.timeout)


class TimeoutHTTP(httplib.HTTP):
    _connection_class = TimeoutHTTPConnection
    
    def set_timeout(self, timeout):
        self._conn.timeout = timeout


class TimeoutTransport(xmlrpclib.Transport):
    
    def __init__(self, timeout=DEFAULT_TIMEOUT, *args, **kwargs):
        xmlrpclib.Transport.__init__(self,*args,**kwargs)
        self.timeout = timeout
    
    def make_connection(self, host):
        conn = TimeoutHTTP(host)
        conn.set_timeout(self.timeout)
        return conn


class CookieTransport(TimeoutTransport):
    '''A subclass of xmlrpclib.Transport that supports cookies.'''
    cookiejar = None
    scheme = 'http'

    # Cribbed from xmlrpclib.Transport.send_user_agent
    def send_cookies(self, connection, cookie_request):
        if self.cookiejar is None:
            self.cookiejar = CookieJar()
        elif self.cookiejar:
            # Let the cookiejar figure out what cookies are appropriate
            self.cookiejar.add_cookie_header(cookie_request)
            # Pull the cookie headers out of the request object...
            cookielist = list()
            for h, v in cookie_request.header_items():
                if h.startswith('Cookie'):
                    cookielist.append([h, v])
            # ...and put them over the connection
            for h, v in cookielist:
                connection.putheader(h, v)

    # This is the same request() method from xmlrpclib.Transport,
    # with a couple additions noted below
    def request(self, host, handler, request_body, verbose = 0):
        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)

        request_url = "%s://%s/" % (self.scheme, host)
        cookie_request = urllib2.Request(request_url)

        self.send_request(h, handler, request_body)
        self.send_host(h, host)
        self.send_cookies(h, cookie_request) # ADDED. creates cookiejar if None.
        self.send_user_agent(h)
        self.send_content(h, request_body)

        errcode, errmsg, headers = h.getreply()

        # ADDED: parse headers and get cookies here
        # fake a response object that we can fill with the headers above
        class CookieResponse:
            def __init__(self, headers): self.headers = headers
            def info(self): return self.headers
        cookie_response = CookieResponse(headers)
        # Okay, extract the cookies from the headers
        self.cookiejar.extract_cookies(cookie_response, cookie_request)
        # And write back any changes
        if hasattr(self.cookiejar, 'save'):
            self.cookiejar.save(self.cookiejar.filename)

        if errcode != 200:
            raise xmlrpclib.ProtocolError(
                host + handler,
                errcode, errmsg,
                headers
                )

        self.verbose = verbose

        try:
            sock = h._conn.sock
        except AttributeError:
            sock = None

        return self._parse_response(h.getfile(), sock)


class SafeCookieTransport(xmlrpclib.SafeTransport, CookieTransport):
    '''SafeTransport subclass that supports cookies.'''
    scheme = 'https'

