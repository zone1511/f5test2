from __future__ import division
from .stats import ResultStats
import Queue
import itertools
import logging
import sys
import threading
import time

# Based on palb module 0.1.1: http://pypi.python.org/pypi/palb
# + Added the LoadManager class for easy access to the core from other modules
# + Added the ability to limit the download rate
# + Removed the daemon mode from the URLProducer and URLGetter threads
# + Added keepalive support
# + Added debug support

__version__ = '0.1.3'
__author__ = 'Oliver Tonnhofer <olt@bogosoft.com>'

#import signal

keep_processing = True
LOG = logging.getLogger('palb.core')
LOCK = threading.RLock()

class Result(object):

    def __init__(self, time, size, status, detail_time = None):
        self.time = time
        self.size = size
        self.status = status
        self.detail_time = detail_time

    def __repr__(self):
        return 'Result(%.5f, %d, %d, detail_time=%r)' % (self.time, self.size,
                                                        self.status, self.detail_time)

class URLGetter(threading.Thread):

    def __init__(self, signup_list, result_queue):
        threading.Thread.__init__(self)
        self.result_queue = result_queue
        signup_list.append(self)
        self.signup_list = signup_list
        self.results_enabled = True
        self.manager = None

    def run(self):
        mng = self.manager
        while keep_processing:
            url = mng.job_request()
            if url is None:
                self.close()
                break
            result = self.get_url(url)
            mng.job_done(url)
            if self.results_enabled:
                self.result_queue.put(result)
        self.signup_list.remove(self)
        LOG.debug('%s done' % self._Thread__name)

    def get_url(self, url):
        return NotImplementedError

try:
    from .getter.curl import url_getter
except ImportError, e:
    from .getter.urllib import url_getter

class URLGetterPool(object):

    def __init__(self, url_queue, size = 2, limit_rate = 0, urls_len = 0):
        self.size = size
        self.limit_rate = limit_rate
        self.urls_len = urls_len
        
        self.keepalive = 0
        self.timeout = 300
        self.debug = False
        self.results_enabled = True
        self.balancing_enabled = True
        self.url_queue = url_queue
        self.result_queue = Queue.Queue()
        self.getters = []
        self.ratios = {}

    def job_request(self):
        secs = 0
        
        while True:
            url = self.url_queue.get()
            if not url:
                return url
            
            if self.balancing_enabled and \
               self.ratios.get(url, 0) >= self.size / self.urls_len:
                time.sleep(secs)
                secs += 0.1
            else:
                secs = 0
                break
        
        LOCK.acquire()
        if not self.ratios.get(url, 0):
            self.ratios[url] = 1
        else:
            self.ratios[url] += 1
        LOCK.release()
        return url

    def job_done(self, url):    
        LOCK.acquire()
        if self.ratios.get(url, 0):
            self.ratios[url] -= 1
        else:
            LOG.error("BUG: Tried to set a negative ratio!")
        LOCK.release()
        
    def start(self):
        self.add(self.size)

    def add(self, n):
        for _ in xrange(n):
            t = url_getter(self.getters, self.result_queue)
            t.manager = self
            if self.limit_rate > 0:
                t.set_rate_limit(self.limit_rate)
            t.results_enabled = self.results_enabled
            t.set_keepalive(self.keepalive)
            t.set_debug(self.debug)
            t.set_timeout(self.timeout)
            t.start()
        self.size = len(self.getters)

    def remove(self, n):
        for _ in xrange(n):
            self.url_queue.put(None)
        self.size -= n

    def stop(self):
        while len(self.getters) > 0:
            LOG.debug('Wait for %d more workers to finish' % len(self.getters))
            time.sleep(1)

class URLProducer(threading.Thread):

    def __init__(self, url_queue, urls, n = 10):
        threading.Thread.__init__(self)
        self.url_queue = url_queue
        self.n = n
        if isinstance(urls, basestring):
            urls = itertools.repeat(urls)
        elif isinstance(urls, list):
            urls = itertools.cycle(urls)
        self.url_iter = urls

    def stop(self):
        if self.url_queue.full():
            self.url_queue.get()

    def run(self):
        global keep_processing
        i = 0
        
        while keep_processing and (self.n < 0 or i < self.n):
            try:
                self.url_queue.put(self.url_iter.next())
            except StopIteration:
                keep_processing = False
                break
            i += 1
        LOG.debug('producer done')

class LoadManager(object):

    def __init__(self, urls, concurrency=1, requests=1, rate=0):
        self.c = concurrency
        self.n = requests
        self.urls = urls
        self.rate = rate

        self.pool = None
        self.producer = None

        url_queue = Queue.Queue(100)
        self.stats = ResultStats()
        self.producer = URLProducer(url_queue, urls, requests)
        self.pool = URLGetterPool(url_queue, concurrency, rate, len(urls))

    def start(self):
        self.producer.start()
        self.pool.start()

    def set_rate(self, n):
        self.rate = n

    def set_keepalive(self, f = True):
        self.pool.keepalive = f

    def set_debug(self, f):
        self.pool.debug = f

    def set_timeout(self, n):
        self.pool.timeout = n

    def toggle_results(self, enable = None):
        if enable is None:
            self.pool.results_enabled = not self.pool.results_enabled
        else:
            self.pool.results_enabled = enable

    def toggle_balancing(self, enable = None):
        if enable is None:
            self.pool.balancing_enabled = not self.pool.balancing_enabled
        else:
            self.pool.balancing_enabled = enable

    def add(self, n):
        if self.pool is None:
            raise Exception('call start() first')
        self.pool.add(n)

    def remove(self, n):
        if self.pool is None:
            raise Exception('call start() first')
        self.pool.remove(n)

    def stop(self):
        global keep_processing
        if self.pool is None:
            raise Exception('call start() first')
        keep_processing = False
        self.stats.stop()
        self.producer.stop()
        self.pool.stop()

    def get_stats(self):
        if self.n < 0:
            self.stop()
            raise Exception('Nonsense in BASIC')
        LOG.debug('Gonna wait for all %d requests to finish...' % self.n)
        for _ in xrange(self.n):
            self.stats.add(self.pool.result_queue.get())

        self.stop()
        return self.stats

    def get_stats_now(self):
        while True:
            try:
                self.stats.add(self.pool.result_queue.get_nowait())
            except Queue.Empty:
                break

        self.stop()
        return self.stats

class PALB(object):

    def __init__(self, urls, c = 1, n = 1):
        self.c = c
        self.n = n
        self.urls = urls

    def start(self):
        out = sys.stdout

        pool = URLGetterPool(self.c)
        pool.start()

        producer = URLProducer(pool.url_queue, self.urls, n = self.n)

        print >> out, 'This is palb, Version', __version__
        print >> out, 'Copyright (c) 2009', __author__
        print >> out, 'Licensed under MIT License'
        print >> out
        print >> out, 'Using %s as URL getter.' % url_getter.name
        print >> out, 'Benchmarking (be patient).....',
        out.flush()

        stats = ResultStats()
        producer.start()

        for _ in xrange(self.n):
            if not keep_processing:
                break
            stats.add(pool.result_queue.get())
        stats.stop()

        print >> out, 'done'
        print >> out
        print >> out
        print >> out, 'Average Document Length: %.0f bytes' % (stats.avg_req_length,)
        print >> out
        print >> out, 'Concurrency Level:    %d' % (self.c,)
        print >> out, 'Time taken for tests: %.3f seconds' % (stats.total_wall_time,)
        print >> out, 'Complete requests:    %d' % (len(stats.results),)
        print >> out, 'Failed requests:      %d' % (stats.failed_requests,)
        print >> out, 'Total transferred:    %d bytes' % (stats.total_req_length,)
        print >> out, 'Requests per second:  %.2f [#/sec] (mean)' % (len(stats.results) /
                                                                    stats.total_wall_time,)
        print >> out, 'Time per request:     %.3f [ms] (mean)' % (stats.avg_req_time * 1000,)
        print >> out, 'Time per request:     %.3f [ms] (mean,'\
                     ' across all concurrent requests)' % (stats.avg_req_time * 1000 / self.c,)
        print >> out, 'Transfer rate:        %.2f [Kbytes/sec] received' % \
                      (stats.total_req_length / stats.total_wall_time / 1024,)
        print >> out

        connection_times = stats.connection_times()
        if connection_times is not None:
            print >> out, 'Connection Times (ms)'
            print >> out, '              min  mean[+/-sd] median   max'
            names = ('Connect', 'Processing', 'Waiting', 'Total')
            for name, data in zip(names, connection_times):
                t_min, t_mean, t_sd, t_median, t_max = [v * 1000 for v in data] # to [ms]
                t_min, t_mean, t_median, t_max = [round(v) for v in t_min, t_mean,
                                                  t_median, t_max]
                print >> out, '%-11s %5d %5d %5.1f %6d %7d' % (name + ':', t_min, t_mean, t_sd,
                                                               t_median, t_max)
            print >> out

        print >> out, 'Percentage of the requests served within a certain time (ms)'
        for percent, seconds in stats.distribution():
            print >> out, ' %3d%% %6.0f' % (percent, seconds * 1024),
            if percent == 100:
                print >> out, '(longest request)'
            else:
                print >> out


def main():
    from optparse import OptionParser
    usage = "usage: %prog [options] url(s)"
    parser = OptionParser(usage = usage, version = '%prog ' + __version__)
    parser.add_option('-c', None, dest = 'c', type = 'int', default = 1,
                      help = 'number of concurrent requests')
    parser.add_option('-n', None, dest = 'n', type = 'int', default = 1,
                      help = 'total number of requests')
    parser.add_option('-u', '--url-func', dest = 'url_func', default = None,
                      help = '''the name of a python function that returns an iterator of
URL strings (package.module:func). the function gets a list with all remaining command
line arguments''')
    parser.add_option('-f', '--url-file', dest = 'url_file', default = None,
                      help = '''file with one URL per line''')

    (options, args) = parser.parse_args()

    if options.url_file is not None:
        if options.url_file == '-':
            urls = [line.strip() for line in sys.stdin]
        else:
            urls = [line.strip() for line in open(options.url_file)]
    elif options.url_func is not None:
        module, func = options.url_func.split(':')
        module = __import__(module)
        urls = getattr(module, func)(args)
    elif len(args) > 0:
        urls = args
    else:
        parser.error('need one or more URL(s) or -u|-f argument')
    palb = PALB(urls, c = options.c, n = options.n)
    palb.start()
