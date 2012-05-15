'''
Created on Jan 25, 2012

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options
import logging
from f5test.utils.palb import LoadManager
import time


LOG = logging.getLogger(__name__)
__version__ = '1.0'


class TrafficGen(Macro):

    def __init__(self, options, urls):
        self.options = Options(options.__dict__)
        self.urls = urls

        super(TrafficGen, self).__init__()

    def setup(self):
        o = self.options
        m = LoadManager(self.urls, concurrency=o.concurrency, 
                        requests=o.requests, rate=o.rate)
        m.set_timeout(o.timeout)
        m.set_results(o.stats)
        
        # XXX: Balancing doesn't work! Should be reworked to use queue 
        # priorities.
        #if o.requests < 0:
        #    LOG.info('Balancing requests.')
        #    m.set_balancing(True)
        
        if o.dns:
            m.set_dns(o.dns)
        m.start()
        LOG.info("Started.")
        
        pattern = map(lambda x:int(x), o.pattern.split(':'))
        
        stopped = False
        i = 0
        countdown = 0
        max_concurrency = 0
        concurrency = o.concurrency
        while 1:
            try:
                if countdown:
                    time.sleep(1)
                    countdown -= 1
                    LOG.info('Running...')
                    if m.producer.done:
                        break
                else:
                    j = i % len(pattern)
                    sleep_or_delta = pattern[j]
                    if j % 2:
                        LOG.debug('Sleep %d seconds', sleep_or_delta)
                        countdown = sleep_or_delta
                        #time.sleep(sleep_or_delta)
                    else:
                        if sleep_or_delta < 0:
                            sleep_or_delta = abs(sleep_or_delta)
                            LOG.debug('Remove %d workers', sleep_or_delta)
                            m.remove(sleep_or_delta)
                            concurrency = concurrency - sleep_or_delta
                        else:
                            LOG.debug('Add %d workers', sleep_or_delta)
                            m.add(sleep_or_delta)
                            concurrency = concurrency + sleep_or_delta
                        max_concurrency = max(concurrency, max_concurrency)
                    i += 1
    
            except KeyboardInterrupt:
                LOG.info("Stopping...")
                stopped = True
                break
        
        if o.requests > 0 and not stopped:
            while not m.producer.url_queue.empty():
                try:
                    time.sleep(0.1)
                except KeyboardInterrupt:
                    stopped = True
                    break

        if o.stats:
            if stopped:
                stats = m.get_stats_so_far()
            else:
                LOG.info("Waiting for pending requests. Hit Ctrl+C at any time to stop.")
                stats = m.get_stats()

        m.stop()
        LOG.info("Done.")

        if o.stats:
            print'Average Document Length: %.0f bytes' % (stats.avg_req_length,)
            print
            print'Max Concurrency Level:    %d' % (max_concurrency,)
            print'Time taken for tests: %.3f seconds' % (stats.total_wall_time,)
            print'Complete requests:    %d' % (len(stats.results),)
            print'Failed requests:      %d' % (stats.failed_requests,)
            print'Total transferred:    %d bytes' % (stats.total_req_length,)
            print'Requests per second:  %.2f [#/sec] (mean)' % (len(stats.results) /
                                                                stats.total_wall_time,)
            print'Time per request:     %.3f [ms] (mean)' % (stats.avg_req_time * 1000,)
            print'Time per request:     %.3f [ms] (mean,'\
                         ' across all concurrent requests)' % (stats.avg_req_time * 1000 / max_concurrency,)
            print'Transfer rate:        %.2f [Kbytes/sec] received' % \
                          (stats.total_req_length / stats.total_wall_time / 1024,)


def main():
    import optparse
    import sys

    usage = """%prog [options] <url> [url]...""" \
    """
  
  Examples:
  %prog https://10.11.41.73/1MB https://10.11.41.69/1MB -v
  %prog https://10.11.41.73/1MB https://10.11.41.69/1MB -s -p 2:300:-2:300"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2, 
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="HTTP/S Traffic Generator %s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug logging")
    p.add_option("-s", "--stats", action="store_true", default=False,
                 help="Show statistics when done (default: no)")
    p.add_option("-k", "--keepalive", action="store_true",
                 help="Reuse HTTP/1.1 connections for subsequent requests")
    
    p.add_option("-c", "--concurrency", metavar="INTEGER",
                 default=1, type="int",
                 help="Number of parallel threads (default: 10)")
    p.add_option("-n", "--requests", metavar="INTEGER",
                 default=-1, type="int",
                 help="Total number of requests (default: -1/infinite)")
    p.add_option("-r", "--rate", metavar="INTEGER",
                 default=1*1024*1024, type="int",
                 help="Maximum bandwidth in bytes per sec (default: 1 Mbps)")
    p.add_option("-d", "--dns", metavar="ADDRESS",
                 default=None, type="string",
                 help="DNS server to use (required for GTM testing)")
    p.add_option("-p", "--pattern", metavar="STRING",
                 default="0:10", type="string",
                 help="[Threads delta:Sleep]... (default: 1:300:-1:300)")
    p.add_option("-t", "--timeout", metavar="SECONDS", type="int", default=10,
                 help="Timeout (default: 10)")

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
