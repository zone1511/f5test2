'''
Created on Jan 4, 2012
Modified on: $DateTime: 2012/08/30 22:32:16 $

@author: jono
'''
import logging
from f5test.utils.wait import wait
LOG = logging.getLogger(__name__)


class LogTester(object):

    def __init__(self, filename, testcb, ifc, timeout=0):
        self.filename = filename
        self.testcb = testcb
        self.timeout = timeout
        self.ifc = ifc

    def __enter__(self):
        ssh = self.ifc.api
        self._pre_stats = ssh.stat(self.filename)

    def __exit__(self, type, value, traceback):  # @ReservedAssignment
        ssh = self.ifc.api

        def callback():
            self._post_stats = ssh.stat(self.filename)

            size_before = self._pre_stats.st_size
            size_after = self._post_stats.st_size
            delta = size_after - size_before
            LOG.debug('delta: %d', delta)

            ret = ssh.run('tail --bytes={0} {1}'.format(delta, self.filename))
            return self.testcb(ret.stdout, self._post_stats)

        if self.timeout:
            wait(callback, timeout=self.timeout)
        else:
            callback()
