'''
Created on Aug 11, 2011

@author: jono
'''
from __future__ import absolute_import
from ..core import URLGetter, Result
from dns.resolver import Resolver
import dns
import logging
import time
import urlparse

LOG = logging.getLogger(__name__)

class DNSURLGetter(URLGetter):
    name = 'dns'
    def __init__(self, signup_list, result_queue):
        URLGetter.__init__(self, signup_list, result_queue)
        self.resolver = Resolver(configure=False)
        self.delay = 0

    def set_rate_limit(self, n):
        self.delay = 1.0 / n

    def set_headers(self, h):
        pass

    def set_debug(self, f):
        pass

    def set_timeout(self, n):
        self.resolver.lifetime = float(n)

    def set_keepalive(self, f):
        pass

    def close(self):
        pass

    def get_url(self, url):
        start = time.time()
        size = status = 0
        resolver = self.resolver
        
        u = urlparse.urlparse(url)
        assert u.scheme == 'dns', "Can't handle scheme: %s" % u.scheme
        resolver.nameservers = [u.netloc]
        qname = u.path.split('/')[1]
        try:
            resolver.query(qname, rdtype=dns.rdatatype.A,
                           rdclass=dns.rdataclass.IN, tcp=False,
                           source=None, raise_on_no_answer=True)
            status = 1
            time.sleep(self.delay)
            #LOG.info(answer)
        except Exception, e:
            #import traceback
            #traceback.print_exc()
            LOG.warning('Failed: %s', repr(e))
            return None
        total_time = time.time() - start
        return Result(total_time, size, status)

url_getter = DNSURLGetter
