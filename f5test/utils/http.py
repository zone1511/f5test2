'''
Created on Jul 17, 2014

@author: jono
'''
from __future__ import absolute_import
import BaseHTTPServer
import ssl
from threading import Thread
import time
import base64
from geventhttpclient import HTTPClient
import gevent.ssl

from f5test.utils.net import get_local_ip, get_open_port
# from .net import get_local_ip


# from .wait import wait
TIMEOUT = 10
MGMT_HOST = 'f5.com'


class BasicAuthRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def parse_request(self):
        BaseHTTPServer.BaseHTTPRequestHandler.parse_request(self)
        self.auth = None
        if 'Authorization' in self.headers:
            mode, value = self.headers['Authorization'].split(' ')
            assert mode, 'Basic'
            self.auth = base64.b64decode(value).split(':')
        return True


class HttpListener(Thread):

    def __init__(self, handler_class, timeout, port=80, debug=False):
        super(HttpListener, self).__init__(name='HttpListener')
        self.handler_class = handler_class
        self.timeout = timeout if timeout > 0 else 10 ** 10
        handler_class.timeout = timeout
        self.port = port
        self.debug = debug

    def run(self):
        server_address = ('', self.port)

        server = BaseHTTPServer.HTTPServer(server_address, self.handler_class)
        server.timeout = self.timeout
        server.running = True
        end = time.time() + self.timeout
        while time.time() < end and server.running:
            server.handle_request()
            if not server.running:
                server.server_close()


def server(handler_class, address=None, port=None, timeout=TIMEOUT,
           debug=False, ssl=False, ssl_version=ssl.PROTOCOL_SSLv23):
    assert callable(handler_class)
    if not address:
        address = get_local_ip(MGMT_HOST)

    if port is None:
        port = get_open_port()
    # Waiting for the port to be released (if already in use)
    t = HttpListener(handler_class, timeout, port, debug)
    t.start()
    return address, port, t


def request(url, method='GET', payload=u'', headers={}, timeout=30):
    """A super-simplistic http/s client with no SSL cert validation.

    >>> print request('http://google.com').status_code
    301
    >>> print request('https://google.com').read()
    <HTML><HEAD>...
    """
    client = HTTPClient.from_url(url, ssl_options={'cert_reqs': gevent.ssl.CERT_NONE},  # @UndefinedVariable
                                 network_timeout=timeout,
                                 connection_timeout=timeout)
    try:
        return client.request(method, url, payload, headers)
    finally:
        client.close()


if __name__ == '__main__':
    class HandlePost(BasicAuthRequestHandler):
        def do_POST(self):
            print 'Got a post!', self.auth
            self.send_response(200)
            self.server.running = False
    a, p, t = server(HandlePost, port=8082, timeout=TIMEOUT)
    print a, p
    t.join()
    print 'done!'
