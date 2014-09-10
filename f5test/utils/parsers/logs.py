'''
Created on Jan 4, 2012
Modified on: $DateTime: 2014/08/01 10:37:30 $

@author: jono
'''
import re
import logging
from f5test.utils.wait import wait
LOG = logging.getLogger(__name__)


class LogTester(object):
    """The generic LogTester class that lets you implement a callback function.
    It also has an embedded wait which waits until the provided callback returns true."""

    def __init__(self, filename, testcb, ifc, timeout=0):
        self.filename = filename
        self.testcb = testcb
        self.timeout = timeout
        self.ifc = ifc

    def __enter__(self):
        self.setup()

    def __exit__(self, type, value, traceback):  # @ReservedAssignment
        self.teardown()

    def setup(self):
        ssh = self.ifc.api
        self._pre_stats = ssh.stat(self.filename)
        return self

    def teardown(self):
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
            return wait(callback, timeout=self.timeout)
        else:
            return callback()


class GrepLogTester(LogTester):
    """A more specific LogTester class that greps the log delta for a specific regex pattern"""

    def __init__(self, filename, ifc, expr=r'.*'):
        self.filename = filename
        self.ifc = ifc
        self.timeout = None

        def testcb(stdout, stats):
            lines = []
            for line in stdout.splitlines():
                if re.search(expr, line):
                    lines.append(line)
            return lines
        self.testcb = testcb
