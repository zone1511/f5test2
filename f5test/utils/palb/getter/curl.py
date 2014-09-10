from __future__ import absolute_import
import sys
import time
import pycurl
import logging
from ..core import URLGetter, Result
from dns.resolver import Resolver
import dns
import urlparse

LOG = logging.getLogger(__name__)

if sys.platform == "win32":
    _null_file = 'nul'
else:
    _null_file = '/dev/null'

class PyCurlURLGetter(URLGetter):
    name = 'pycurl'
    fp = open(_null_file, "wb")
    def __init__(self, signup_list, result_queue):
        URLGetter.__init__(self, signup_list, result_queue)
        self.c =  pycurl.Curl()
        self.c.setopt(pycurl.WRITEDATA, self.fp)
        self.c.setopt(pycurl.MAXCONNECTS, 1)
        self.c.setopt(pycurl.SSL_VERIFYHOST, 0)
        self.c.setopt(pycurl.SSL_VERIFYPEER, 0)
        self.c.setopt(pycurl.NOSIGNAL, 1)
        self.headers = []
        self.dns = None
        self.resolver = Resolver(configure=False)

    def set_rate_limit(self, n):
        self.c.setopt(pycurl.MAX_RECV_SPEED_LARGE, int(n))

    def set_headers(self, h):
        self.headers = h
        self.c.setopt(pycurl.HTTPHEADER, self.headers)

    def set_debug(self, f):
        self.c.setopt(pycurl.VERBOSE, int(f))

    def set_timeout(self, n):
        LOG.debug('%s set_timeout %d', self._Thread__name, n)
        self.c.setopt(pycurl.TIMEOUT, int(n))

    def set_dns(self, dns):
        self.dns = dns

    def set_keepalive(self, f):
        if f:
            self.headers += ['Connection: Keep-Alive']
            self.c.setopt(pycurl.HTTPHEADER, self.headers)
            self.c.setopt(pycurl.FORBID_REUSE, 0)
            self.c.setopt(pycurl.FRESH_CONNECT, 0)
        else:
            self.c.setopt(pycurl.FORBID_REUSE, 1)
            self.c.setopt(pycurl.FRESH_CONNECT, 1)

    def close(self):
        self.c.close()

    def get_url(self, url):
        if self.dns:
            self.resolver.nameservers = [self.dns]
            u = urlparse.urlparse(url)
            qname = u.hostname
            answer = self.resolver.query(qname, rdtype=dns.rdatatype.A,
                                    rdclass=dns.rdataclass.IN, tcp=False,
                                    source=None, raise_on_no_answer=False)
            if answer.response.answer:
                ip = answer.response.answer[0].items[0].address
                if u.port:
                    netloc = '%s:%d' % (ip, u.netloc.split(':')[1])
                else:
                    netloc = ip
                url = urlparse.urlunsplit((u[0], netloc, u[2], u[3], u[4]))
                self.c.setopt(pycurl.HTTPHEADER, self.headers + ['Host: %s' % qname])

        url = str(url)
        self.c.setopt(pycurl.URL, url)
        try:
            self.c.perform()
        except Exception, e:
            # to avoid hogging the CPU in case of repeated errors
            time.sleep(.1)
            LOG.warn("curl barfed on '%s': %s", url, e)
        status = self.c.getinfo(pycurl.RESPONSE_CODE)
        size = self.c.getinfo(pycurl.SIZE_DOWNLOAD)
        t_total = self.c.getinfo(pycurl.TOTAL_TIME)
        t_connect = self.c.getinfo(pycurl.CONNECT_TIME)
        t_start = self.c.getinfo(pycurl.STARTTRANSFER_TIME)
        t_proc = t_total - t_connect
        return Result(t_total, size, status, detail_time=(t_connect, t_proc, t_start))

url_getter = PyCurlURLGetter
