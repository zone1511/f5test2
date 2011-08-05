import os
import urllib2
import time
import logging
from ..core import URLGetter, Result

LOG = logging.getLogger(__name__)

# urllib2 does some lazy loading. so we do a dummy request here to get more
# acurate results for the first request
f=os.path.abspath(__file__)
if f[:1] != '/':
    f = '/' + f
_prime_url = 'file://'+f
urllib2.urlopen(_prime_url).read()

class URLLibURLGetter(URLGetter):
    name = 'urllib'
    def __init__(self, signup_list, result_queue):
        URLGetter.__init__(self, signup_list, result_queue)
        self.opener = urllib2.build_opener()

    def set_rate_limit(self, n):
        LOG.warning('set_rate_limit - Not implemented')

    def set_headers(self, h):
        LOG.warning('set_headers - Not implemented')

    def set_debug(self, f):
        LOG.warning('set_debug - Not implemented')

    def set_timeout(self, n):
        LOG.warning('set_timeout - Not implemented')

    def set_keepalive(self, f):
        LOG.warning('set_keepalive - Not implemented')

    def close(self):
        LOG.warning('close - Not implemented')

    def get_url(self, url):
        start = time.time()
        size = status = 0
        try:
            result = self.opener.open(url)
            size = len(result.read())
            status = result.code
        except urllib2.HTTPError, e:
            size = len(e.read())
            status = e.code
        except:
            import traceback
            traceback.print_exc()
            return None
        total_time = time.time() - start
        return Result(total_time, size, status)

url_getter = URLLibURLGetter
