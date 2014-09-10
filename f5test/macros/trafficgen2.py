'''
Created on Apr 3, 2012

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options
from f5test.utils.stb import RateLimit, TokenBucket
import gevent  # @UnusedImport
import gevent.pool
from geventhttpclient import HTTPClient, URL
from ssl import PROTOCOL_TLSv1, CERT_NONE
from dns.resolver import Resolver
import dns
import itertools
import logging
import time
import urlparse

DEFAULT_TIMEOUT = 3
DEFAULT_LIMIT = 90
LOG = logging.getLogger(__name__)
__version__ = '0.3'


def partition(size, n):
    q, r = divmod(size, n)
    indices = [q * i + min(i, r) for i in range(n + 1)]
    return [indices[i + 1] - indices[i] for i in range(n)]


class TrafficGen(Macro):

    def __init__(self, options, urls):
        options.setdefault('timeout', DEFAULT_TIMEOUT)
        options.setdefault('limit', DEFAULT_LIMIT)
        self.options = Options(options)
        self.urls = urls

        super(TrafficGen, self).__init__()

    def make_client(self, url):
        o = self.options
        headers = {'Connection': 'Keep-Alive' if o.keepalive else 'Close'}
        resolver = Resolver(configure=False)

        if o.dns:
            resolver.nameservers = [o.dns]
            u = urlparse.urlparse(url)
            qname = u.hostname
            answer = resolver.query(qname, rdtype=dns.rdatatype.A,
                                    rdclass=dns.rdataclass.IN, tcp=False,
                                    source=None, raise_on_no_answer=False)

            if answer.response.answer:
                ip = answer.response.answer[0].items[0].address
                if u.port:
                    netloc = '%s:%d' % (ip, u.netloc.split(':')[1])
                else:
                    netloc = ip
                url = urlparse.urlunsplit((u[0], netloc, u[2], u[3], u[4]))
                headers['Host'] = qname

        client = HTTPClient.from_url(url, concurrency=o.concurrency,
                                     connection_timeout=o.timeout,
                                     network_timeout=o.timeout,
                                     headers=headers,
                                     ssl_options=dict(ssl_version=PROTOCOL_TLSv1,
                                                      cert_reqs=CERT_NONE)
                                     )
        return client

    def setup(self):
        o = self.options
        assert o.concurrency > 0, "Number of concurrent threads must be positive."

        def run(client, url):
            qs = url.request_uri
            with gevent.Timeout(o.timeout):
                while True:
                    try:
                        response = client.get(qs)
                        break
                    except Exception, e:
                        LOG.debug("Connect %s: %s", url, e)
                        gevent.sleep(0.1)
                        continue
            #response.read()
            #assert response.status_code == 200

            block_size = 256 * 1024  # 256KB
            #block_size = 4096
            #block_size = 1024
            block_count = 0
            kbps = o.rate
            bucket = TokenBucket(1000 * kbps, kbps)
            rate_limiter = RateLimit(bucket)

            rate_limiter(block_count, block_size)
            while True:
                try:
                    block = response.read(block_size)
                except Exception, e:
                    LOG.warning("Read %s: %s", url, e)
                    break

                if not block or response.parser_failed():
                    break
                block_count += 1
                rate_limiter(block_count, len(block))

        def superrun(url, group):
            client = self.make_client(url)
            for i, url in enumerate(itertools.repeat(url)):
                group.spawn(run, client, URL(url))
                if i + 1 == o.requests:
                    break
            group.join(timeout=o.limit)

        LOG.info('Running...')
        # Create individual Pools for each URL
        groups = {}
        for i, size in enumerate(partition(o.concurrency, len(self.urls))):
            groups[self.urls[i]] = gevent.pool.Pool(size=size or 1)

        # Spin up one thread worker per URL
        supergroup = gevent.pool.Pool(size=len(self.urls))
        now = time.time()
        for url in self.urls:
            supergroup.spawn(superrun, url, groups[url])

        try:
            supergroup.join(timeout=o.limit, raise_error=True)
            supergroup.kill()
        except KeyboardInterrupt:
            supergroup.kill()

        delta = time.time() - now
        #req_per_sec = o.requests / delta

        LOG.info("delta: %f seconds" % delta)

    def cleanup(self):
        """Shutdown gevent as it seems to be leaking some globals."""
        super(TrafficGen, self).cleanup()
        gevent.get_hub().destroy()


def main():
    import optparse
    import sys

    usage = """%prog [options] <url> [url]...""" \
    """

  Examples:
  %prog https://10.11.41.73/1MB https://10.11.41.69/1MB -v
  """

    formatter = optparse.TitledHelpFormatter(indent_increment=2,
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="HTTP/S Traffic Generator %s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug logging")
#    p.add_option("-s", "--stats", action="store_true", default=False,
#                 help="Show statistics when done (default: no)")
    p.add_option("-k", "--keepalive", action="store_true", default=False,
                 help="Reuse HTTP/1.1 connections for subsequent requests")

    p.add_option("-c", "--concurrency", metavar="INTEGER",
                 default=1, type="int",
                 help="Number of parallel threads (default: 10)")
    p.add_option("-n", "--requests", metavar="INTEGER",
                 default=10, type="int",
                 help="Total number of requests (default: 10)")
    p.add_option("-r", "--rate", metavar="INTEGER",
                 default=100, type="int",
                 help="Maximum bandwidth in Kbytes per sec (default: 100 KB/s)")
    p.add_option("-d", "--dns", metavar="ADDRESS",
                 default=None, type="string",
                 help="Use this DNS server to resolve hostnames.")
#    p.add_option("-p", "--pattern", metavar="STRING",
#                 default="0:10", type="string",
#                 help="[Threads delta:Sleep]... (default: 1:300:-1:300)")
    p.add_option("-t", "--timeout", metavar="SECONDS", type="int",
                 default=DEFAULT_TIMEOUT, help="Timeout (default: %d)" % DEFAULT_TIMEOUT)
    p.add_option("-l", "--limit", metavar="SECONDS", type="int",
                 default=DEFAULT_LIMIT, help="Run limit (default: %d)" % DEFAULT_LIMIT)

    options, args = p.parse_args()

    if options.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        logging.getLogger('f5test').setLevel(logging.INFO)
        logging.getLogger('f5test.macros').setLevel(logging.INFO)

    LOG.setLevel(level)
    logging.basicConfig(level=level)

    if not args:
        p.print_version()
        p.print_help()
        sys.exit(2)

    cs = TrafficGen(options=options, urls=args)
    cs.run()


if __name__ == '__main__':
    main()
