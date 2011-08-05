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


class TimeoutTransport(xmlrpclib.Transport):
    
    def __init__(self, timeout=DEFAULT_TIMEOUT, *args, **kwargs):
        xmlrpclib.Transport.__init__(self, *args, **kwargs)
        self.timeout = timeout
    
    def make_connection(self, host):
        #return an existing connection if possible.  This allows
        #HTTP/1.1 keep-alive.
        if self._connection and host == self._connection[0]:
            return self._connection[1]

        # create a HTTP connection object from a host descriptor
        chost, self._extra_headers, _ = self.get_host_info(host)
        #store the host argument along with the connection object
        self._connection = host, httplib.HTTPConnection(chost, 
                                                        timeout=self.timeout)
        return self._connection[1]


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

    def single_request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request

        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)

        request_url = "%s://%s/" % (self.scheme, host)
        cookie_request = urllib2.Request(request_url)

        try:
            self.send_request(h, handler, request_body)
            self.send_host(h, host)
            self.send_cookies(h, cookie_request) # ADDED. creates cookiejar if None.
            self.send_user_agent(h)
            self.send_content(h, request_body)

            response = h.getresponse(buffering=True)

            # ADDED: parse headers and get cookies here
            # fake a response object that we can fill with the headers above
            class CookieResponse:
                def __init__(self, headers): self.headers = headers
                def info(self): return self.headers
            cookie_response = CookieResponse(response.msg)
            # Okay, extract the cookies from the headers
            self.cookiejar.extract_cookies(cookie_response, cookie_request)
            # And write back any changes
            if hasattr(self.cookiejar, 'save'):
                self.cookiejar.save(self.cookiejar.filename)

            if response.status == 200:
                self.verbose = verbose
                return self.parse_response(response)
        except xmlrpclib.Fault:
            raise
        except Exception:
            # All unexpected errors leave connection in
            # a strange state, so we clear it.
            self.close()
            raise

        #discard any response data and raise exception
        if (response.getheader("content-length", 0)):
            response.read()
        raise xmlrpclib.ProtocolError(
            host + handler,
            response.status, response.reason,
            response.msg,
            )


class SafeCookieTransport(xmlrpclib.SafeTransport, CookieTransport):
    '''SafeTransport subclass that supports cookies.'''
    scheme = 'https'

